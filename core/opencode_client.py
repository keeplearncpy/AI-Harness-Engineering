"""
Harness Engine — OpenCode HTTP API Client.
Wraps the OpenCode server REST API for programmatic agent invocation.
"""

import logging
from typing import Any, Optional

import httpx
from core.config import settings

log = logging.getLogger("harness.opencode_client")


class OpenCodeClient:
    """Client for OpenCode's HTTP server API (opencode serve)."""

    def __init__(self, base_url: str = None):
        self.base_url = base_url or f"http://{settings.opencode_host}:{settings.opencode_port}"
        self._client = httpx.AsyncClient(timeout=settings.opencode_timeout)

    # ---------------------------------------------------------------
    # Health
    # ---------------------------------------------------------------

    async def ping(self) -> bool:
        try:
            r = await self._client.get(f"{self.base_url}/global/health")
            return r.status_code == 200
        except Exception:
            return False

    # ---------------------------------------------------------------
    # Agent Listing
    # ---------------------------------------------------------------

    async def list_agents(self) -> list[dict]:
        r = await self._client.get(f"{self.base_url}/agent")
        r.raise_for_status()
        return r.json()

    # ---------------------------------------------------------------
    # Session Management
    # ---------------------------------------------------------------

    async def create_session(self, title: str = "Harness Pipeline") -> str:
        r = await self._client.post(
            f"{self.base_url}/session",
            json={"title": title},
        )
        r.raise_for_status()
        return r.json()["id"]

    async def delete_session(self, session_id: str) -> bool:
        r = await self._client.delete(f"{self.base_url}/session/{session_id}")
        return r.status_code == 200

    # ---------------------------------------------------------------
    # Prompt / Agent Invocation
    # ---------------------------------------------------------------

    async def prompt(
        self,
        session_id: str,
        text: str,
        agent: Optional[str] = None,
        model: Optional[str] = None,
        system: Optional[str] = None,
        no_reply: bool = False,
    ) -> dict:
        """Send a prompt to a session, optionally using a specific agent."""
        body: dict[str, Any] = {
            "parts": [{"type": "text", "text": text}],
        }
        if agent:
            body["agent"] = agent
        if model:
            body["model"] = model
        if system:
            body["system"] = system
        if no_reply:
            body["noReply"] = True

        r = await self._client.post(
            f"{self.base_url}/session/{session_id}/message",
            json=body,
        )
        r.raise_for_status()
        return r.json()

    async def prompt_agent(
        self,
        session_id: str,
        agent: str,
        text: str,
        model: Optional[str] = None,
    ) -> dict:
        """Convenience: send a prompt using a specific agent."""
        return await self.prompt(session_id, text, agent=agent, model=model)

    async def command(
        self,
        session_id: str,
        command: str,
        arguments: str = "",
    ) -> dict:
        """Execute a slash command in a session."""
        r = await self._client.post(
            f"{self.base_url}/session/{session_id}/command",
            json={"command": command, "arguments": arguments},
        )
        r.raise_for_status()
        return r.json()

    # ---------------------------------------------------------------
    # Messages
    # ---------------------------------------------------------------

    async def list_messages(self, session_id: str, limit: int = 50) -> list[dict]:
        r = await self._client.get(
            f"{self.base_url}/session/{session_id}/message",
            params={"limit": limit},
        )
        r.raise_for_status()
        return r.json()

    # ---------------------------------------------------------------
    # File Operations
    # ---------------------------------------------------------------

    async def read_file(self, path: str) -> str:
        r = await self._client.get(
            f"{self.base_url}/file/content",
            params={"path": path},
        )
        r.raise_for_status()
        return r.text

    async def file_status(self) -> list[dict]:
        r = await self._client.get(f"{self.base_url}/file/status")
        r.raise_for_status()
        return r.json()

    # ---------------------------------------------------------------
    # Cleanup
    # ---------------------------------------------------------------

    async def close(self):
        await self._client.aclose()


# Singleton
opencode_client = OpenCodeClient()
