"""
Harness Engine — Teams Notification Helper.
Sends Adaptive Cards and messages to Microsoft Teams channels.
"""

import json
import logging
from datetime import datetime, timezone

import httpx
from core.config import settings
from core.models import PipelineState, ConversationContext

log = logging.getLogger("harness.teams_notifier")


class TeamsNotifier:
    """Send messages to Teams via incoming webhook."""

    def __init__(self):
        self._client = httpx.AsyncClient(timeout=30)
        self.webhook_url = settings.teams_webhook_url

    @property
    def is_configured(self) -> bool:
        return bool(self.webhook_url)

    async def _send(self, payload: dict):
        if not self.is_configured:
            log.info(f"Teams webhook not configured, skip notification: {payload.get('summary', '')}")
            return

        try:
            r = await self._client.post(self.webhook_url, json=payload)
            r.raise_for_status()
            log.info(f"Teams notification sent: {payload.get('summary', '')[:80]}")
        except Exception as e:
            log.error(f"Failed to send Teams notification: {e}")

    # ===============================================================
    # Phase Updates
    # ===============================================================

    async def send_phase_update(self, state: PipelineState, phase_name: str, agent: str):
        await self._send({
            "@type": "MessageCard",
            "@context": "https://schema.org/extensions",
            "summary": f"[{state.run_id}] Phase {state.current_phase}: {phase_name} completed",
            "themeColor": "0076D7",
            "title": f"Phase {state.current_phase}: {phase_name} ✅",
            "text": f"Agent **{agent}** completed successfully.\n\n"
                    f"Pipeline: {state.project_name}\n"
                    f"Progress: {state.current_phase}/{state.total_phases} phases",
            "sections": [{
                "facts": [
                    {"name": "Run ID", "value": state.run_id},
                    {"name": "Agent", "value": agent},
                    {"name": "Status", "value": "Completed"},
                ]
            }],
        })

    # ===============================================================
    # CI/CD Approval Card
    # ===============================================================

    async def send_approval_card(self, state: PipelineState, conv: ConversationContext):
        await self._send({
            "@type": "MessageCard",
            "@context": "https://schema.org/extensions",
            "summary": f"[{state.run_id}] CI/CD Approval Required",
            "themeColor": "FFA500",
            "title": "CI/CD Pipeline — Manual Approval Required",
            "text": (
                f"All code generation, testing, and review phases are complete.\n\n"
                f"**Project**: {state.project_name}\n"
                f"**Run ID**: {state.run_id}\n"
                f"**Requirements**: {conv.confirmed_requirements[:300]}\n\n"
                f"Please review and approve the deployment."
            ),
            "potentialAction": [
                {
                    "@type": "HttpPOST",
                    "name": "Approve & Deploy",
                    "target": f"{{settings.host}}:{{settings.port}}/webhook/approval",
                    "body": json.dumps({
                        "run_id": state.run_id,
                        "approved": True,
                        "action": "approve",
                    }),
                },
                {
                    "@type": "HttpPOST",
                    "name": "Reject",
                    "target": f"{{settings.host}}:{{settings.port}}/webhook/approval",
                    "body": json.dumps({
                        "run_id": state.run_id,
                        "approved": False,
                        "action": "reject",
                    }),
                },
            ],
        })

    # ===============================================================
    # Completion
    # ===============================================================

    async def send_completion(self, state: PipelineState, conv: ConversationContext):
        await self._send({
            "@type": "MessageCard",
            "@context": "https://schema.org/extensions",
            "summary": f"[{state.run_id}] Pipeline Completed",
            "themeColor": "2ECC40",
            "title": "Pipeline Complete!",
            "text": (
                f"All phases completed successfully.\n\n"
                f"**Project**: {state.project_name}\n"
                f"**Run ID**: {state.run_id}\n"
                f"**Started**: {state.started_at}\n"
                f"**Completed**: {state.completed_at}"
            ),
        })

    # ===============================================================
    # Error / Rejection
    # ===============================================================

    async def send_rejection(self, state: PipelineState, conv: ConversationContext, comments: str):
        await self._send({
            "@type": "MessageCard",
            "@context": "https://schema.org/extensions",
            "summary": f"[{state.run_id}] CI/CD Rejected",
            "themeColor": "FF4136",
            "title": "CI/CD Rejected",
            "text": f"Deployment was rejected.\n\n**Comments**: {comments}",
        })

    async def send_error(self, run_id: str, error: str, channel_id: str):
        await self._send({
            "@type": "MessageCard",
            "@context": "https://schema.org/extensions",
            "summary": f"[{run_id}] Pipeline Error",
            "themeColor": "FF4136",
            "title": "Pipeline Error",
            "text": f"An error occurred during execution:\n\n```\n{error[:500]}\n```",
        })

    async def close(self):
        await self._client.aclose()


teams_notifier = TeamsNotifier()
