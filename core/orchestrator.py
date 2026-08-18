"""
Harness Engine — 编排器（Agent Loop）。
AI Harness Engineering 的大脑，负责：
  1. 澄清循环：向聊天平台追问 → 记录到云效任务
  2. 流水线执行：FSD → 数据 → 代码 → 测试 → 评审
  3. CI/CD 审批：审批卡片 → 人工确认 → 触发流水线
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
from core.notifier import notifier
from core.messaging import UnifiedMessage

log = logging.getLogger("harness.orchestrator")


class Orchestrator:
    """流水线编排器 —— agent loop 引擎。"""

    def __init__(self):
        # 闲聊会话缓存：key = "platform:chat_id" → opencode session_id
        self._chat_sessions: dict[str, str] = {}

    @staticmethod
    def _agent(key: str) -> str:
        """按角色取实际 agent 名（见 settings.agent_map）。"""
        return settings.agent_map.get(key, key)

    async def start(self):
        log.info("编排器已启动 — 等待触发")

    async def stop(self):
        log.info("编排器已停止")

    # ===============================================================
    # 入口：平台无关消息（飞书 / 钉钉 / ...）
    # ===============================================================

    async def handle_message(self, msg: UnifiedMessage) -> Optional[str]:
        """
        所有聊天平台的统一入口。
        平台不带 run_id 时通过 (platform, chat_id) 关联后续消息，
        再委托给既有的对话/流水线流程。返回可选的回复文本。

        多机器人场景：msg.agent 由对应飞书应用配置决定，
        实现一个机器人一个 agent。
        """
        try:
            return await self._handle_message(msg)
        except Exception as e:
            log.error(f"[{msg.platform}] 处理消息失败 {msg.message_id}: {e}")
            return "抱歉，内部服务暂时不可用（OpenCode 引擎可能未启动），请稍后再试。"

    async def _handle_message(self, msg: UnifiedMessage) -> Optional[str]:
        # 先让 opencode 判断意图：闲聊直接回复，项目请求走流水线
        classification = await self._chat_classify(msg)

        if classification.startswith("NEW_PROJECT"):
            # 项目开发请求 → 进入澄清/流水线流程
            return await self._start_project_flow(msg, msg.agent or self._agent("clarify"))
        return classification

    async def _chat_classify(self, msg: UnifiedMessage) -> str:
        """把消息交给 opencode 主 agent：闲聊详细回复；项目请求返回 NEW_PROJECT 标记。"""
        chat_key = f"{msg.platform}:{msg.chat_id}"
        session_id = self._chat_sessions.get(chat_key)
        if not session_id:
            session_id = await opencode_client.create_session(f"Chat-{msg.platform}-{msg.chat_id}")
            self._chat_sessions[chat_key] = session_id

        prompt = f"""
用户发来一条消息：

{msg.text}

请判断意图：
- 如果用户明确要创建 / 开发 / 构建软件项目
  （如"帮我建一个xxx项目"、"开发一个xxx系统"、"做一个xxx应用"），
  请只回复一行：NEW_PROJECT
- 否则，请直接详细地回答这条消息（闲聊、问答、分析等），
  回答要详尽、结构化、有深度。

用中文回答。"""
        result = await opencode_client.prompt_agent(session_id, self._agent("chat"), prompt)
        return (self._extract_text(result) or "").strip()

    async def _start_project_flow(self, msg: UnifiedMessage, agent: str) -> Optional[str]:
        """项目请求进入既有的澄清/流水线流程。"""
        reply_to_run_id = ""

        # 关联 (platform, chat_id) 对应的澄清线程
        if msg.chat_id:
            state = state_manager.find_by_chat(msg.platform, msg.chat_id)
            if state is not None:
                reply_to_run_id = state.run_id
                log.info(f"[{reply_to_run_id}] 收到 {msg.platform} 会话 {msg.chat_id} 的后续消息")

        payload = TeamsWebhookPayload(
            text=msg.text,
            user=msg.user_name or msg.user_id or "unknown",
            channel_id=msg.chat_id,
            channel_name="",
            conversation_id=msg.chat_id,
            reply_to_run_id=reply_to_run_id,
        )

        result = await self.handle_teams_trigger(payload, agent=agent)

        # 在会话上打上平台标识，便于后续关联
        run_id = result.get("run_id", "")
        if run_id:
            state = state_manager.get(run_id)
            if state is not None and state.conversation is not None:
                state.conversation.platform = msg.platform
                state.conversation.platform_chat_id = msg.chat_id
                state.conversation.agent = agent
                state_manager.save(state)
                self._save_conversation(state.conversation)

        return result.get("reply", "") or None

    # ===============================================================
    # 入口：Teams 触发
    # ===============================================================

    async def handle_teams_trigger(self, payload: TeamsWebhookPayload,
                                   agent: str = None) -> dict:
        """
        处理收到的 Teams 消息。
        返回可直接作为 Teams 回复的 dict。
        """
        if agent is None:
            agent = self._agent("clarify")

        # 是否为澄清线程的回复
        if payload.reply_to_run_id:
            return await self._handle_clarification_reply(payload)

        # 新请求
        run_id = str(uuid.uuid4())[:8]
        original_text = payload.text or payload.description

        log.info(f"[{run_id}] 收到新请求: {original_text[:100]}...")

        # --- 阶段 0：澄清循环 ---
        return await self._start_clarification(run_id, original_text, payload, agent)

    # ===============================================================
    # 阶段 0：澄清循环
    # ===============================================================

    async def _start_clarification(
        self, run_id: str, user_message: str, payload: TeamsWebhookPayload,
        agent: str = None,
    ) -> dict:
        """启动澄清阶段：创建云效任务，循环提问。"""
        if agent is None:
            agent = self._agent("clarify")

        session_id = await opencode_client.create_session(f"Clarify-{run_id}")

        # 会话状态
        conv = ConversationContext(
            run_id=run_id,
            state=ConversationState.CLARIFYING,
            original_message=user_message,
            agent=agent,
            teams_channel_id=payload.channel_id,
            teams_user=payload.user,
        )

        # 调用绑定 agent（多机器人时各自绑定）分析需求。
        # 云效任务创建为尽力而为：无权限（403）时直接跳过，继续澄清。
        prompt = f"""
You are the {agent}. A user just submitted a new project request:

USER REQUEST:
{user_message}

TASK:
1. Try to create a task/story in Yunxiao for this request (via MCP).
   If the token has no permission (e.g. 403), SKIP this step silently and continue.
2. Analyze the requirements. Determine if they are clear enough to proceed.
3. If requirements are UNCLEAR (missing scope, ambiguous features, no tech details):
   - Ask ONE specific follow-up question to clarify.
   - Format your response as: QUESTION: <your question>
   - Keep it concise — one question at a time.
4. If requirements are CLEAR:
   - Respond: CONFIRMED: <summary of confirmed requirements>

Respond in Chinese."""
        result = await opencode_client.prompt_agent(session_id, agent, prompt)
        response_text = self._extract_text(result)

        # 保存对话记录
        conv.rounds.append(ClarificationRound(
            round=1,
            question=response_text,
            answer="",
        ))
        self._save_conversation(conv)

        # 保存初始状态
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

        # 需求已明确则直接进入流水线
        if response_text.startswith("CONFIRMED:"):
            return await self._requirements_confirmed(state, conv, response_text)

        # 把问题返回聊天平台
        return {
            "reply": response_text,
            "run_id": run_id,
            "state": "clarifying",
            "awaiting_reply": True,
        }

    async def _handle_clarification_reply(self, payload: TeamsWebhookPayload) -> dict:
        """处理用户对澄清问题的回答。"""
        run_id = payload.reply_to_run_id
        state = state_manager.get(run_id)
        if state is None or state.conversation is None:
            return {"reply": f"未知会话: {run_id}，请发起新的请求。", "run_id": run_id}

        conv = state.conversation
        user_answer = payload.text

        # 记录上一轮的回答
        if conv.rounds:
            conv.rounds[-1].answer = user_answer

        log.info(f"[{run_id}] 澄清回答: {user_answer[:100]}...")
        round_num = len(conv.rounds) + 1

        # 交给绑定 agent 做下一轮分析
        agent = conv.agent or self._agent("clarify")
        prompt = f"""
The user answered the previous clarification question. Here is the context:

ORIGINAL REQUEST: {conv.original_message}

PREVIOUS QUESTION: {conv.rounds[-1].question if conv.rounds else 'N/A'}
USER ANSWER: {user_answer}

TASK:
1. Try to update the Yunxiao task with this new information (via MCP).
   If the token has no permission (e.g. 403), SKIP this step silently and continue.
2. Determine if requirements are now clear enough.
3. If still UNCLEAR — ask ONE more specific question. Format: QUESTION: <question>
4. If CLEAR — respond: CONFIRMED: <full summary of confirmed requirements>

Respond in Chinese. Be concise."""
        result = await opencode_client.prompt_agent(state.session_id, agent, prompt)
        response_text = self._extract_text(result)

        # 新增一轮
        conv.rounds.append(ClarificationRound(
            round=round_num,
            question=response_text,
            answer="",
        ))
        state.phases.append(PhaseStatus(
            phase_name="clarification",
            status="running",
            agent=agent,
            result_summary=f"第 {round_num} 轮: {response_text[:100]}",
        ))

        if len(conv.rounds) >= conv.max_rounds:
            # 达到最大轮数，用现有信息收尾
            response_text = f"CONFIRMED: 达到最大轮数，使用现有信息:\n{conv.original_message}\n用户回答: {json.dumps([r.answer for r in conv.rounds])}"

        # 需求已明确则进入 FSD
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
        """需求已确认，进入真正的流水线。"""
        conv.state = ConversationState.CONFIRMED
        conv.confirmed_requirements = confirmed_text.replace("CONFIRMED:", "").strip()
        state.conversation = conv
        state.status = "running"
        state.current_phase = 1
        self._save_conversation(conv)
        state_manager.save(state)

        # 把最终确认的需求记录到云效任务（尽力而为，无权限则跳过）
        await opencode_client.prompt_agent(
            state.session_id, conv.agent or self._agent("clarify"),
            f"Try to record the final confirmed requirements in the Yunxiao task (skip silently if no permission):\n{conv.confirmed_requirements}"
        )

        # 后台启动流水线
        import asyncio
        asyncio.create_task(self._run_pipeline(state, conv))

        return {
            "reply": f"✅ 需求已确认！流水线已启动。\n\n**需求摘要**:\n{conv.confirmed_requirements[:500]}",
            "run_id": state.run_id,
            "state": "running",
            "phase": "流水线已启动: FSD 生成中...",
        }

    # ===============================================================
    # 流水线执行
    # ===============================================================

    async def _run_pipeline(self, state: PipelineState, conv: ConversationContext):
        """需求确认后执行完整流水线。"""
        run_id = state.run_id
        try:
            # ---- 阶段 1: FSD（含技术选型，写入 fsd/）----
            await self._run_phase(state, 1, "requirements", self._agent("fsd"), f"""
Generate a Functional Specification Document based on these confirmed requirements:

{conv.confirmed_requirements}

Requirements:
1. Write the SSD to fsd/SSD-SystemOverview.md including a 技术选型 (tech stack) section
   covering frontend, backend, database and middleware. Decide the stack from the request;
   default: Frontend React 19 + Vite + TypeScript; Backend Java 21 + Spring Boot 3.x + Maven;
   Database MySQL 8.
2. Write feature FSDs under fsd/{{模块}}/feature-{{功能名}}-{{索引}}.md
   and update fsd/INDEX.md.
3. Include user stories, acceptance criteria, data entities, and API endpoints.
Output in Chinese.""",
                "fsd/SSD-SystemOverview.md")

            # ---- 阶段 2a: 前端原型 ----
            await self._run_phase(state, 2, "prototype", self._agent("prototype"),
                "Generate the HTML wireframe prototype under prototype/ based on the FSD "
                "pages/routes/menus/forms, including prototype/click-map.md. "
                "No images, no AI aesthetics — plain HTML+CSS wireframes with real click navigation.",
                "prototype/click-map.md")

            # ---- 阶段 2b: 数据建模 ----
            await self._run_phase(state, 2, "data_modeling", self._agent("data_modeler"),
                "Based on the FSD and the SSD 技术选型 (tech stack), design the complete database "
                "schema with DDL matching the chosen database dialect. "
                "Generate DDL SQL, ER diagram (Mermaid), and data dictionary under design/.",
                "design/db-schema.sql")

            # ---- 阶段 3: 代码生成（技术栈来自 SSD，不写死）----
            await self._run_phase(state, 3, "generation", self._agent("backend_dev"),
                "Generate the backend code under backend/ following the tech stack specified in "
                "fsd/SSD-SystemOverview.md 技术选型 section. "
                "Implement all API endpoints, services, models, and middleware.",
                "backend/")
            await self._run_phase(state, 3, "generation_fe", self._agent("frontend_dev"),
                "Generate the frontend code under frontend/ following the tech stack in "
                "fsd/SSD-SystemOverview.md and the pages/routes in prototype/click-map.md. "
                "Implement all pages, components, services, and routing.",
                "frontend/")

            # ---- 阶段 4: 测试 ----
            await self._run_phase(state, 4, "testing", self._agent("tester"),
                "Generate comprehensive tests for the generated code. Cover unit, integration, and E2E scenarios.",
                "tests/")

            # ---- 阶段 5: 代码评审 ----
            await self._run_phase(state, 5, "review", self._agent("reviewer"),
                "Review ALL generated code for quality, security vulnerabilities (OWASP Top 10), performance issues, and best practices. Generate a structured review report.",
                "reviews/")

            # ---- 阶段 6: CI/CD 审批（渠道由 NOTIFY_CHANNEL 决定，默认飞书）----
            conv.state = ConversationState.WAITING_APPROVAL
            state.status = "waiting_approval"
            state.current_phase = 6
            state_manager.save(state)
            self._save_conversation(conv)

            # 发送审批卡片（飞书卡片按钮 / Teams 审批卡片）
            await notifier.send_approval_card(state, conv)

            log.info(f"[{run_id}] 等待 CI/CD 人工审批（渠道: {settings.notify_channel}）...")

        except Exception as e:
            log.error(f"[{run_id}] 流水线失败: {e}")
            state.status = "failed"
            state.error_message = str(e)
            state_manager.save(state)
            await observability.end_run(state)
            await notifier.send_error(run_id, str(e), self._conv_chat_id(conv))

    # ===============================================================
    # 审批与部署
    # ===============================================================

    async def handle_approval(self, body: dict):
        """处理 CI/CD 人工审批（飞书卡片按钮 / Teams / Power Automate）。"""
        run_id = body.get("run_id")
        approved = body.get("approved", False)
        comments = body.get("comments", "")
        chat_id = body.get("chat_id", "")

        state = state_manager.get(run_id)
        if state is None:
            log.warning(f"未知运行的审批: {run_id}")
            return

        conv = state.conversation

        if approved:
            log.info(f"[{run_id}] CI/CD 已批准，触发部署...")
            state.status = "deploying"
            state_manager.save(state)

            # 通过绑定 agent 触发部署
            await opencode_client.prompt_agent(
                state.session_id, conv.agent or self._agent("clarify"),
                f"Trigger the CI/CD deployment pipeline for run {run_id}. Approved by: {body.get('user', 'unknown')}. Comments: {comments}"
            )

            state.status = "completed"
            state.completed_at = datetime.now(timezone.utc).isoformat()
            state_manager.save(state)
            conv.state = ConversationState.COMPLETED
            self._save_conversation(conv)
            await observability.end_run(state)

            await notifier.send_completion(state, conv, chat_id=chat_id)

        else:
            log.info(f"[{run_id}] CI/CD 已拒绝: {comments}")
            state.status = "rejected"
            state_manager.save(state)
            conv.state = ConversationState.FAILED
            self._save_conversation(conv)
            await notifier.send_rejection(state, conv, comments, chat_id=chat_id)

    async def handle_card_action(self, value: dict):
        """处理飞书卡片按钮回调（card.action.trigger 的 value）。"""
        run_id = value.get("run_id", "")
        if not run_id:
            log.warning("卡片动作缺少 run_id，忽略")
            return
        body = {
            "run_id": run_id,
            "approved": bool(value.get("approved", False)),
            "comments": value.get("comments", ""),
            "user": value.get("user", ""),
            "chat_id": value.get("chat_id", ""),
        }
        log.info(f"卡片审批动作: run={run_id} approved={body['approved']}")
        await self.handle_approval(body)

    # ===============================================================
    # 编程接口（CLI 触发）
    # ===============================================================

    async def new_project(self, description: str, options: dict = None) -> str:
        """编程式触发（来自 CLI，非聊天平台）。"""
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
            total_phases=7,
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
    # 内部辅助
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

        log.info(f"[{state.run_id}] 阶段 {phase_num}: {agent} — {phase_name}")

        result = await opencode_client.prompt_agent(state.session_id, agent, prompt)
        result_text = self._extract_text(result)[:200]

        state.phases[-1].status = "completed"
        state.phases[-1].completed_at = datetime.now(timezone.utc).isoformat()
        state.phases[-1].result_summary = result_text
        state.phases[-1].output_path = output_path
        state_manager.save(state)

        await observability.record_phase(state.run_id, agent, phase_name, "success", {"summary": result_text})

        # 通知聊天平台（渠道由 NOTIFY_CHANNEL 决定，默认飞书）
        await notifier.send_phase_update(state, phase_name, agent)

    @staticmethod
    def _conv_chat_id(conv: ConversationContext) -> str:
        if conv is None:
            return ""
        return conv.platform_chat_id or conv.teams_channel_id or ""

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


# 单例
orchestrator = Orchestrator()
