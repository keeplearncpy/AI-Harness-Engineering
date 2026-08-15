"""
Harness Engine — OpenCode HTTP API 客户端。
封装 OpenCode 服务的 REST API，用于程序化调用 agent。
"""

import logging
from typing import Any, Optional

import httpx
from core.config import settings

log = logging.getLogger("harness.opencode_client")


class OpenCodeClient:
    """OpenCode HTTP 服务（opencode serve）的客户端。"""

    def __init__(self, base_url: str = None):
        self.base_url = base_url or f"http://{settings.opencode_host}:{settings.opencode_port}"
        self._client = httpx.AsyncClient(timeout=settings.opencode_timeout)

    # ---------------------------------------------------------------
    # 健康检查
    # ---------------------------------------------------------------

    async def ping(self) -> bool:
        try:
            r = await self._client.get(f"{self.base_url}/global/health")
            return r.status_code == 200
        except Exception:
            return False

    # ---------------------------------------------------------------
    # Agent 列表
    # ---------------------------------------------------------------

    async def list_agents(self) -> list[dict]:
        r = await self._client.get(f"{self.base_url}/agent")
        r.raise_for_status()
        return r.json()

    # ---------------------------------------------------------------
    # 会话管理
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
    # Prompt / Agent 调用
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
        """向会话发送 prompt，可指定使用的 agent。"""
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
        """便捷方法：使用指定 agent 发送 prompt。"""
        return await self.prompt(session_id, text, agent=agent, model=model)

    async def command(
        self,
        session_id: str,
        command: str,
        arguments: str = "",
    ) -> dict:
        """在会话中执行斜杠命令。"""
        r = await self._client.post(
            f"{self.base_url}/session/{session_id}/command",
            json={"command": command, "arguments": arguments},
        )
        r.raise_for_status()
        return r.json()

    # ---------------------------------------------------------------
    # 消息
    # ---------------------------------------------------------------

    async def list_messages(self, session_id: str, limit: int = 50) -> list[dict]:
        r = await self._client.get(
            f"{self.base_url}/session/{session_id}/message",
            params={"limit": limit},
        )
        r.raise_for_status()
        return r.json()

    # ---------------------------------------------------------------
    # 文件操作
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
    # 清理
    # ---------------------------------------------------------------

    async def close(self):
        await self._client.aclose()


# 单例
opencode_client = OpenCodeClient()
