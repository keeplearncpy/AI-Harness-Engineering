"""
Harness Engine — 消息接入层（平台无关的消息接收）。

对外暴露：
  * UnifiedMessage / PlatformAdapter — 设计契约
  * MessageRouter — webhook 分发与监听器生命周期
"""

from core.messaging.base import (
    UnifiedMessage,
    PlatformAdapter,
    WebhookResult,
    MessageCallback,
)
from core.messaging.router import MessageRouter, message_router

__all__ = [
    "UnifiedMessage",
    "PlatformAdapter",
    "WebhookResult",
    "MessageCallback",
    "MessageRouter",
    "message_router",
]
