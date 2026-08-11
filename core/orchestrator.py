"""
Harness Engine — Orchestrator (Agent Loop).
The brain of AI Harness Engineering. Manages:
  1. Clarification loop: ask Teams follow-up questions → save to Yunxiao task
  2. Pipeline execution: FSD → Data → Code → Test → Review
  3. CI/CD approval: Teams approval card → manual review → trigger pipeline
"""

import uuid
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from core.state_manager import state_manager
from core.opencode_client import opencode_client
from core.observability import observability
from core.models import (
    TeamsWebhookPayload,
    PipelineState,
    PhaseStatus,
    ConversationContext,
    ConversationState,
    ClarificationRound,
)
from core.config import settings
from core.teams_notifier import teams_notifier

log = logging.getLogger("harness.orchestrator")


class Orchestrator:
    """Pipeline orchestrator — the agent loop engine."""

    async def start(self):
        log.info("Orchestrator started — waiting for triggers")

    async def stop(self):
        log.info("Orchestrator stopped")

    # ===============================================================
    # Entry: Teams Trigger
    # ===============================================================

    async def handle_teams_trigger(self, payload: TeamsWebhookPayload) -> dict:
        """
        Process an incoming Teams message.
        Returns a dict that can be sent back as a Teams reply.
        """

        # Check if this is a reply to an existing clarification thread
        if payload.reply_to_run_id:
            return await self._handle_clarification_reply(payload)

        # New request
        run_id = str(uuid.uuid4())[:8]
        original_text = payload.text or payload.description

        log.info(f"[{run_id}] New request from Teams: {original_text[:100]}...")

        # --- Phase 0: Clarification Loop ---
        # Ask yunxiao-agent (via OpenCode MCP) to create a task and clarify requirements
        return await self._start_clarification(run_id, original_text, payload)

    # ===============================================================
    # Phase 0: Clarification Loop
    # ===============================================================

    async def _start_clarification(
        self, run_id: str, user_message: str, payload: TeamsWebhookPayload
    ) -> dict:
        """Start the clarification phase. Creates Yunxiao task, asks questions loop."""

        session_id = await opencode_client.create_session(f"Clarify-{run_id}")

        # Conversation state
        conv = ConversationContext(
            run_id=run_id,
            state=ConversationState.CLARIFYING,
            original_message=user_message,
            teams_channel_id=payload.channel_id,
            teams_user=payload.user,
        )

        # Call zentao-agent or yunxiao-agent to create a task and review requirements
        prompt = f"""
You are the yunxiao-agent. A user just submitted a new project request via Teams:

USER REQUEST:
{user_message}

TASK:
1. Create a task/story in Yunxiao for this request (via MCP).
2. Analyze the requirements. Determine if they are clear enough to proceed.
3. If requirements are UNCLEAR (missing scope, ambiguous features, no tech details):
   - Ask ONE specific follow-up question to clarify.
   - Format your response as: QUESTION: <your question>
   - Keep it concise — one question at a time.
4. If requirements are CLEAR:
   - Respond: CONFIRMED: <summary of confirmed requirements>
   - Include the Yunxiao task ID and link.

Respond in Chinese."""
        result = await opencode_client.prompt_agent(session_id, "harness-yunxiao-agent", prompt)
        response_text = self._extract_text(result)

        # Save conversation record
        conv.rounds.append(ClarificationRound(
            round=1,
            question=response_text,
            answer="",
        ))
        self._save_conversation(conv)

        # Save initial state
        state = PipelineState(
            run_id=run_id,
            project_name=f"project-{run_id}",
            workflow="new_project",
            current_phase=0,
            total_phases=7,
            status="clarifying",
            session_id=session_id,
            started_at=datetime.now(timezone.utc).isoformat(),
            conversation=conv,
        )
        state_manager.save(state)
        await observability.start_run(state)

        # If requirements already confirmed, jump to pipeline
        if response_text.startswith("CONFIRMED:"):
            return await self._requirements_confirmed(state, conv, response_text)

        # Send question back to Teams
        return {
            "reply": response_text,
            "run_id": run_id,
            "state": "clarifying",
            "awaiting_reply": True,
        }

    async def _handle_clarification_reply(self, payload: TeamsWebhookPayload) -> dict:
        """Handle a user's reply to a clarification question."""
        run_id = payload.reply_to_run_id
        state = state_manager.get(run_id)
        if state is None or state.conversation is None:
            return {"reply": f"Unknown session: {run_id}. Please start a new request.", "run_id": run_id}

        conv = state.conversation
        user_answer = payload.text

        # Record the answer in the last round
        if conv.rounds:
            conv.rounds[-1].answer = user_answer

        log.info(f"[{run_id}] Clarification reply: {user_answer[:100]}...")
        round_num = len(conv.rounds) + 1

        # Send to agent for another round of analysis
        prompt = f"""
The user answered the previous clarification question. Here is the context:

ORIGINAL REQUEST: {conv.original_message}

PREVIOUS QUESTION: {conv.rounds[-1].question if conv.rounds else 'N/A'}
USER ANSWER: {user_answer}

TASK:
1. Update the Yunxiao task with this new information (via MCP).
2. Determine if requirements are now clear enough.
3. If still UNCLEAR — ask ONE more specific question. Format: QUESTION: <question>
4. If CLEAR — respond: CONFIRMED: <full summary of confirmed requirements>

Respond in Chinese. Be concise."""
        result = await opencode_client.prompt_agent(state.session_id, "harness-yunxiao-agent", prompt)
        response_text = self._extract_text(result)

        # Add new round
        conv.rounds.append(ClarificationRound(
            round=round_num,
            question=response_text,
            answer="",
        ))
        state.phases.append(PhaseStatus(
            phase_name="clarification",
            status="running",
            agent="harness-yunxiao-agent",
            result_summary=f"Round {round_num}: {response_text[:100]}",
        ))

        if len(conv.rounds) >= conv.max_rounds:
            # Force stop — take whatever we have
            response_text = f"CONFIRMED: Max rounds reached. Using available info:\n{conv.original_message}\nUser answers: {json.dumps([r.answer for r in conv.rounds])}"

        # If confirmed, proceed to FSD
        if response_text.startswith("CONFIRMED:"):
            return await self._requirements_confirmed(state, conv, response_text)

        self._save_conversation(conv)
        state_manager.save(state)

        return {
            "reply": response_text,
            "run_id": run_id,
            "state": "clarifying",
            "awaiting_reply": True,
            "round": round_num,
        }

    async def _requirements_confirmed(
        self, state: PipelineState, conv: ConversationContext, confirmed_text: str
    ) -> dict:
        """Requirements are confirmed. Proceed to the actual pipeline."""
        conv.state = ConversationState.CONFIRMED
        conv.confirmed_requirements = confirmed_text.replace("CONFIRMED:", "").strip()
        state.conversation = conv
        state.status = "running"
        state.current_phase = 1
        self._save_conversation(conv)
        state_manager.save(state)

        # Record to Yunxiao task (final confirmation)
        await opencode_client.prompt_agent(
            state.session_id, "harness-yunxiao-agent",
            f"Record the final confirmed requirements in the Yunxiao task:\n{conv.confirmed_requirements}"
        )

        # Fire pipeline in background
        import asyncio
        asyncio.create_task(self._run_pipeline(state, conv))

        return {
            "reply": f"✅ Requirements confirmed! Pipeline started.\n\n**Summary**:\n{conv.confirmed_requirements[:500]}",
            "run_id": state.run_id,
            "state": "running",
            "phase": "Pipeline started: FSD generation in progress...",
        }

    # ===============================================================
    # Pipeline Execution
    # ===============================================================

    async def _run_pipeline(self, state: PipelineState, conv: ConversationContext):
        """Execute the full pipeline after requirements are confirmed."""
        run_id = state.run_id
        try:
            # ---- Phase 1: FSD ----
            await self._run_phase(state, 1, "requirements", "harness-fsd", f"""
Generate a Functional Specification Document based on these confirmed requirements:

{conv.confirmed_requirements}

Follow the harness-fsd skill. Generate structured FSD documents with user stories, acceptance criteria, data entities, and API endpoints. Output in Chinese.""",
                "docs/SSD-SystemOverview.md")

            # ---- Phase 2: Data Model ----
            await self._run_phase(state, 2, "data_modeling", "harness-data-modeler",
                "Based on the FSD generated above, design the complete database schema. Generate DDL SQL, ER diagram (Mermaid), and data dictionary.",
                "design/db-schema.sql")

            # ---- Phase 3: Code Generation ----
            await self._run_phase(state, 3, "generation", "harness-backend-dev",
                "Generate FastAPI backend code based on the FSD and DB schema. Implement all API endpoints, services, models, and middleware.",
                "src/backend/")
            await self._run_phase(state, 3, "generation_fe", "harness-frontend-dev",
                "Generate React + TypeScript frontend code based on the FSD and API design. Implement all pages, components, services, and routing.",
                "src/frontend/")

            # ---- Phase 4: Testing ----
            await self._run_phase(state, 4, "testing", "harness-tester",
                "Generate comprehensive tests for the generated code. Cover unit, integration, and E2E scenarios. Follow the harness-testing skill.",
                "tests/")

            # ---- Phase 5: Code Review ----
            await self._run_phase(state, 5, "review", "harness-reviewer",
                "Review ALL generated code for quality, security vulnerabilities (OWASP Top 10), performance issues, and best practices. Generate a structured review report.",
                "reviews/")

            # ---- Phase 6: CI/CD Approval ----
            conv.state = ConversationState.WAITING_APPROVAL
            state.status = "waiting_approval"
            state.current_phase = 6
            state_manager.save(state)
            self._save_conversation(conv)

            # Send Teams approval card
            await teams_notifier.send_approval_card(state, conv)

            log.info(f"[{run_id}] Waiting for CI/CD manual approval...")

        except Exception as e:
            log.error(f"[{run_id}] Pipeline failed: {e}")
            state.status = "failed"
            state.error_message = str(e)
            state_manager.save(state)
            await observability.end_run(state)
            await teams_notifier.send_error(run_id, str(e), conv.teams_channel_id)

    # ===============================================================
    # Approval & Deployment
    # ===============================================================

    async def handle_approval(self, body: dict):
        """Handle CI/CD manual approval from Teams/Power Automate."""
        run_id = body.get("run_id")
        approved = body.get("approved", False)
        comments = body.get("comments", "")

        state = state_manager.get(run_id)
        if state is None:
            log.warning(f"Approval for unknown run: {run_id}")
            return

        conv = state.conversation

        if approved:
            log.info(f"[{run_id}] CI/CD APPROVED. Triggering deploy...")
            state.status = "deploying"
            state_manager.save(state)

            # Deploy via yunxiao-agent (MCP)
            await opencode_client.prompt_agent(
                state.session_id, "harness-yunxiao-agent",
                f"Trigger the CI/CD deployment pipeline for run {run_id}. Approved by: {body.get('user', 'unknown')}. Comments: {comments}"
            )

            state.status = "completed"
            state.completed_at = datetime.now(timezone.utc).isoformat()
            state_manager.save(state)
            conv.state = ConversationState.COMPLETED
            self._save_conversation(conv)
            await observability.end_run(state)

            await teams_notifier.send_completion(state, conv)

        else:
            log.info(f"[{run_id}] CI/CD REJECTED: {comments}")
            state.status = "rejected"
            state_manager.save(state)
            conv.state = ConversationState.FAILED
            self._save_conversation(conv)
            await teams_notifier.send_rejection(state, conv, comments)

    # ===============================================================
    # Programmatic API (CLI trigger)
    # ===============================================================

    async def new_project(self, description: str, options: dict = None) -> str:
        """Programmatic trigger (from CLI, not Teams)."""
        options = options or {}
        run_id = options.get("run_id", str(uuid.uuid4())[:8])

        conv = ConversationContext(
            run_id=run_id,
            state=ConversationState.CONFIRMED,
            original_message=description,
            confirmed_requirements=description,
        )

        state = PipelineState(
            run_id=run_id,
            project_name=options.get("project", f"project-{run_id}"),
            workflow="new_project",
            current_phase=1,
            total_phases=6,
            status="running",
            session_id=await opencode_client.create_session(f"CLI-{run_id}"),
            started_at=datetime.now(timezone.utc).isoformat(),
            conversation=conv,
        )
        state_manager.save(state)
        await observability.start_run(state)

        import asyncio
        asyncio.create_task(self._run_pipeline(state, conv))
        return run_id

    # ===============================================================
    # Internal Helpers
    # ===============================================================

    async def _run_phase(self, state: PipelineState, phase_num: int,
                         phase_name: str, agent: str, prompt: str,
                         output_path: str = ""):
        state.current_phase = phase_num
        state.phases.append(PhaseStatus(
            phase_name=phase_name,
            status="running",
            agent=agent,
            started_at=datetime.now(timezone.utc).isoformat(),
        ))
        state_manager.save(state)

        log.info(f"[{state.run_id}] Phase {phase_num}: {agent} — {phase_name}")

        result = await opencode_client.prompt_agent(state.session_id, agent, prompt)
        result_text = self._extract_text(result)[:200]

        state.phases[-1].status = "completed"
        state.phases[-1].completed_at = datetime.now(timezone.utc).isoformat()
        state.phases[-1].result_summary = result_text
        state.phases[-1].output_path = output_path
        state_manager.save(state)

        await observability.record_phase(state.run_id, agent, phase_name, "success", {"summary": result_text})

        # Notify Teams
        if state.conversation and state.conversation.teams_channel_id:
            await teams_notifier.send_phase_update(state, phase_name, agent)

    def _extract_text(self, result: dict) -> str:
        try:
            parts = result.get("parts", [])
            texts = [p.get("text", "") for p in parts if p.get("type") == "text"]
            return "\n".join(texts)
        except Exception:
            return str(result)

    def _save_conversation(self, conv: ConversationContext):
        import json
        from pathlib import Path
        path = Path(__file__).parent.parent / ".harness" / "conversations" / f"{conv.run_id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(conv.model_dump(mode="json"), f, indent=2, ensure_ascii=False)

    async def get_state(self, run_id: str) -> Optional[PipelineState]:
        return state_manager.get(run_id)


# Singleton
orchestrator = Orchestrator()
