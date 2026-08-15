"""
Harness Engine — 消息接入抽象层。

平台无关的消息接收设计。每个聊天平台（飞书、Teams、钉钉、Slack……）
把自己特有的 webhook / 推送协议适配为 UnifiedMessage，
编排器（orchestrator）无需接触任何平台私有载荷。

每种平台支持两种接入模式：
  * webhook（事件订阅）：平台把事件 POST 给我们
  * listener（长连接 / 轮询）：我们主动建立连接

接入新平台的步骤：
  1. 继承 PlatformAdapter 并实现各抽象方法。
  2. 在 core/messaging/router.py 中注册适配器。
  3. 在 core/config.py 和 .env 中补充凭证配置。
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Awaitable, Callable, Optional

from fastapi import Request
from pydantic import BaseModel, Field

log = logging.getLogger("harness.messaging")

# 统一回调：接收 UnifiedMessage，返回可选的回复文本
MessageCallback = Callable[["UnifiedMessage"], Awaitable[Optional[str]]]


class UnifiedMessage(BaseModel):
    """平台无关的统一消息模型。"""

    platform: str                        # "lark" | "teams" | "dingtalk" | ...
    message_id: str = ""                 # 平台消息 ID（用于 API 回复）
    chat_id: str = ""                    # 会话 / 群 / 频道 ID
    chat_type: str = ""                  # "p2p" | "group" | "channel" | ...
    text: str = ""                       # 纯文本消息内容
    user_id: str = ""                    # 平台用户标识（open_id 等）
    user_name: str = ""
    reply_to_message_id: str = ""        # 线程回复时的被回复消息 ID
    mentioned_bot: bool = False          # 是否 @ 了机器人（群聊）
    timestamp: str = ""
    app_id: str = ""                     # 来源应用 ID（多机器人时区分）
    agent: str = ""                      # 该应用绑定的处理 agent
    raw: dict = Field(default_factory=dict)  # 平台原始载荷（调试用）

    @property
    def is_reply(self) -> bool:
        return bool(self.reply_to_message_id)


class WebhookResult(BaseModel):
    """事件订阅模式下归一化的 webhook 响应。"""

    status: str = "ok"                   # "ok" | "challenge" | "ignored" | "error"
    body: dict = Field(default_factory=dict)
    status_code: int = 200


class PlatformAdapter(ABC):
    """
    聊天平台接入的抽象契约。

    实现类负责把平台特有事件翻译成 UnifiedMessage，
    并通过平台的发消息 API 将回复送回。
    """

    platform: str = "base"

    def __init__(self, on_message: Optional[MessageCallback] = None):
        self.on_message = on_message

    # -------------------------------------------------------------
    # 生命周期 / 能力
    # -------------------------------------------------------------

    @abstractmethod
    def is_configured(self) -> bool:
        """该平台所需凭证是否齐全。"""

    @abstractmethod
    async def start_listener(self, on_message: MessageCallback) -> Optional[asyncio.Task]:
        """
        启动主动接入（长连接 / 轮询）。
        返回后台任务；平台未配置或不使用该模式时返回 None。
        """

    @abstractmethod
    async def handle_webhook(self, request: Request) -> WebhookResult:
        """
        处理一个 webhook 请求（事件订阅模式）。
        必须快速应答（平台对超时会重试）；耗时处理放到后台任务。
        """

    # -------------------------------------------------------------
    # 回复
    # -------------------------------------------------------------

    @abstractmethod
    async def send_reply(self, msg: UnifiedMessage, text: str) -> bool:
        """把回复投递回消息来源会话。"""

    # -------------------------------------------------------------
    # 公共辅助：分发回调并回复
    # -------------------------------------------------------------

    async def _process(self, msg: UnifiedMessage):
        """执行统一回调，并把返回的回复文本发回。"""
        try:
            reply = await self.on_message(msg) if self.on_message else None
            if reply:
                ok = await self.send_reply(msg, reply)
                if not ok:
                    log.warning(f"[{self.platform}] 回复失败: {msg.message_id}")
        except Exception as e:
            log.error(f"[{self.platform}] 处理消息失败 {msg.message_id}: {e}")

    @staticmethod
    def _parse_json(text: str) -> dict:
        try:
            data = json.loads(text)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}
