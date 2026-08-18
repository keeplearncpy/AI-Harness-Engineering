"""
Harness Engine — 消息路由。

维护 平台名 → 适配器 的注册表，支持同一平台注册多个实例
（例如多个飞书机器人：一个机器人绑定一个 agent），
并为所有已注册平台提供统一的 webhook 入口。
"""

import asyncio
import logging
from typing import Optional

from fastapi import HTTPException

from core.config import settings
from core.messaging.base import (
    MessageCallback,
    PlatformAdapter,
    WebhookResult,
)
from core.messaging.lark import LarkAdapter

log = logging.getLogger("harness.messaging.router")


class MessageRouter:
    """持有平台适配器并分发 webhook / 监听任务。"""

    def __init__(self):
        self._adapters: dict[str, list[PlatformAdapter]] = {}

    # -------------------------------------------------------------
    # 注册表
    # -------------------------------------------------------------

    def register(self, adapter: PlatformAdapter):
        self._adapters.setdefault(adapter.platform, []).append(adapter)
        log.info(f"[messaging] 注册平台适配器: {adapter.platform}")

    def get(self, platform: str) -> Optional[list[PlatformAdapter]]:
        return self._adapters.get(platform)

    def get_one(self, platform: str, name: Optional[str] = None) -> Optional[PlatformAdapter]:
        """按名称取单个适配器；未指定名称时要求该平台只有一个实例。"""
        adapters = self._adapters.get(platform, [])
        if name:
            for a in adapters:
                if getattr(a, "name", "") == name:
                    return a
            return None
        if len(adapters) == 1:
            return adapters[0]
        return None

    @property
    def platforms(self) -> list[str]:
        return list(self._adapters.keys())

    def adapters(self, platform: Optional[str] = None) -> list[PlatformAdapter]:
        """返回全部（或指定平台的）适配器实例。"""
        if platform:
            return list(self._adapters.get(platform, []))
        return [a for lst in self._adapters.values() for a in lst]

    # -------------------------------------------------------------
    # 统一回调绑定
    # -------------------------------------------------------------

    def bind(self, on_message: MessageCallback):
        """把编排器回调绑定到所有适配器。"""
        for adapter in self.adapters():
            adapter.on_message = on_message

    def bind_card_actions(self, on_card_action):
        """把卡片按钮回调（审批等）绑定到所有适配器。"""
        for adapter in self.adapters():
            adapter.on_card_action = on_card_action

    # -------------------------------------------------------------
    # webhook 入口（事件订阅模式）
    # -------------------------------------------------------------

    async def handle_webhook(self, platform: str, request,
                             name: Optional[str] = None) -> WebhookResult:
        adapters = self.get(platform)
        if not adapters:
            raise HTTPException(status_code=404, detail=f"未知平台: {platform}")

        adapter = self.get_one(platform, name)
        if adapter is None:
            names = ", ".join(getattr(a, "name", "?") for a in adapters)
            raise HTTPException(
                status_code=400,
                detail=f"平台 {platform} 注册了多个应用（{names}），"
                       f"请使用带应用名的端点 /webhook/{platform}/<应用名>",
            )
        if not adapter.is_configured():
            raise HTTPException(status_code=400, detail=f"平台未配置: {platform}")
        return await adapter.handle_webhook(request)

    # -------------------------------------------------------------
    # listener 入口（长连接 / 轮询模式）
    # -------------------------------------------------------------

    async def start_listeners(self, on_message: MessageCallback) -> list[asyncio.Task]:
        """启动所有适配器的主动接入，返回已启动的任务列表。"""
        self.bind(on_message)
        tasks: list[asyncio.Task] = []
        for adapter in self.adapters():
            task = await adapter.start_listener(on_message)
            if task is not None:
                tasks.append(task)
        return tasks

    async def stop_listeners(self, tasks: list[asyncio.Task]):
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


# 单例：按配置注册所有支持的平台应用。
# 多机器人场景下每个飞书应用对应一个 LarkAdapter 实例。
message_router = MessageRouter()
for _app in settings.lark_apps:
    message_router.register(LarkAdapter(
        app_id=_app["app_id"],
        app_secret=_app["app_secret"],
        name=_app.get("name", "lark"),
        agent=_app.get("agent", ""),
        verification_token=_app.get("verification_token", ""),
        encrypt_key=_app.get("encrypt_key", ""),
    ))
