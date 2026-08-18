"""
Harness Engine — 出站通知器（渠道可配置）。

通过 .env 的 NOTIFY_CHANNEL 决定出站通知（阶段更新、CI/CD 审批卡片、
完成/拒绝/错误）走哪些渠道：

  feishu — 飞书消息审批（默认）：interactive 卡片 + 按钮回调 card.action.trigger
  teams  — Microsoft Teams：incoming webhook + Power Automate 审批
  both   — 同时发送到 feishu 与 teams
  none   — 关闭出站通知（仅日志）

编排器只依赖 Notifier，不感知具体平台。
"""

import json
import logging

from core.config import settings
from core.messaging import message_router
from core.teams_notifier import teams_notifier

log = logging.getLogger("harness.notifier")

# 飞书卡片 header 模板颜色
LARK_HEADER_BLUE = "blue"
LARK_HEADER_GREEN = "green"
LARK_HEADER_ORANGE = "orange"
LARK_HEADER_RED = "red"


class Notifier:
    """渠道无关的出站通知器。"""

    # -------------------------------------------------------------
    # 渠道解析
    # -------------------------------------------------------------

    @property
    def _channels(self) -> list[str]:
        channels = settings.notify_channels
        if "both" in channels:
            return ["feishu", "teams"]
        return [c for c in channels if c in ("feishu", "teams")]

    def _lark(self):
        """用于出站通知的飞书适配器（LARK_NOTIFY_APP 或第一个已配置应用）。"""
        adapters = message_router.adapters("lark")
        if not adapters:
            return None
        if settings.lark_notify_app:
            for a in adapters:
                if getattr(a, "name", "") == settings.lark_notify_app:
                    return a
        return adapters[0]

    @staticmethod
    def _chat_id(conv) -> str:
        if conv is None:
            return ""
        return conv.platform_chat_id or conv.teams_channel_id or ""

    # -------------------------------------------------------------
    # 飞书卡片构造与发送
    # -------------------------------------------------------------

    @staticmethod
    def _card(title: str, color: str, body_md: str, actions: list | None = None) -> dict:
        card = {
            "config": {"wide_screen_mode": True},
            "header": {
                "template": color,
                "title": {"tag": "plain_text", "content": title},
            },
            "elements": [{"tag": "div", "text": {"tag": "lark_md", "content": body_md}}],
        }
        if actions:
            card["elements"].append({"tag": "action", "actions": actions})
        return card

    async def _notify_feishu(self, conv, card: dict, chat_id: str = ""):
        lark = self._lark()
        cid = chat_id or self._chat_id(conv)
        if lark is None or not lark.is_configured():
            log.info("[notifier] 飞书未配置，跳过通知")
            return
        if not cid:
            log.info("[notifier] 无会话 chat_id，跳过飞书通知")
            return
        await lark.send_message(cid, "interactive", json.dumps(card, ensure_ascii=False))

    async def _notify_teams(self, method: str, *args, **kwargs):
        """委托给 teams_notifier（未配置时其内部会跳过）。"""
        await getattr(teams_notifier, method)(*args, **kwargs)

    # -------------------------------------------------------------
    # 对外通知方法（按渠道分发）
    # -------------------------------------------------------------

    async def send_phase_update(self, state, phase_name: str, agent: str):
        """阶段完成通知。"""
        run_id = getattr(state, "run_id", "")
        for channel in self._channels:
            if channel == "feishu":
                await self._notify_feishu(
                    state.conversation,
                    self._card(
                        f"阶段 {state.current_phase}: {phase_name} ✅",
                        LARK_HEADER_BLUE,
                        f"Agent **{agent}** 执行完成\n\n"
                        f"项目: {state.project_name}\n"
                        f"进度: {state.current_phase}/{state.total_phases}\n"
                        f"Run ID: {run_id}",
                    ),
                )
            elif channel == "teams":
                await self._notify_teams("send_phase_update", state, phase_name, agent)

    async def send_approval_card(self, state, conv, chat_id: str = ""):
        """CI/CD 审批卡片。飞书默认：卡片按钮 approve/reject。"""
        cid = chat_id or self._chat_id(conv)
        for channel in self._channels:
            if channel == "feishu":
                await self._notify_feishu(
                    conv,
                    self._card(
                        "CI/CD 人工审批",
                        LARK_HEADER_ORANGE,
                        f"代码生成、测试、评审全部完成，等待人工审批。\n\n"
                        f"**项目**: {state.project_name}\n"
                        f"**Run ID**: {state.run_id}\n"
                        f"**需求**: {conv.confirmed_requirements[:200]}",
                        actions=[
                            {
                                "tag": "button",
                                "text": {"tag": "plain_text", "content": "✅ 批准并部署"},
                                "type": "primary",
                                "value": {"run_id": state.run_id, "approved": True, "chat_id": cid},
                            },
                            {
                                "tag": "button",
                                "text": {"tag": "plain_text", "content": "❌ 拒绝"},
                                "type": "danger",
                                "value": {"run_id": state.run_id, "approved": False, "chat_id": cid},
                            },
                        ],
                    ),
                )
            elif channel == "teams":
                await self._notify_teams("send_approval_card", state, conv)

    async def send_completion(self, state, conv, chat_id: str = ""):
        """流水线完成通知。"""
        for channel in self._channels:
            if channel == "feishu":
                await self._notify_feishu(
                    conv,
                    self._card(
                        "流水线完成 🎉",
                        LARK_HEADER_GREEN,
                        f"**项目**: {state.project_name}\n"
                        f"**Run ID**: {state.run_id}\n"
                        f"**开始**: {state.started_at}\n"
                        f"**完成**: {state.completed_at}",
                    ),
                    chat_id=chat_id,
                )
            elif channel == "teams":
                await self._notify_teams("send_completion", state, conv)

    async def send_rejection(self, state, conv, comments: str, chat_id: str = ""):
        """CI/CD 拒绝通知。"""
        for channel in self._channels:
            if channel == "feishu":
                await self._notify_feishu(
                    conv,
                    self._card(
                        "CI/CD 已拒绝",
                        LARK_HEADER_RED,
                        f"部署被拒绝。\n\n**备注**: {comments}",
                    ),
                    chat_id=chat_id,
                )
            elif channel == "teams":
                await self._notify_teams("send_rejection", state, conv, comments)

    async def send_error(self, run_id: str, error: str, chat_id: str = ""):
        """流水线错误通知。"""
        for channel in self._channels:
            if channel == "feishu":
                if not chat_id:
                    continue
                await self._notify_feishu(
                    None,
                    self._card(
                        "流水线错误",
                        LARK_HEADER_RED,
                        f"执行出错:\n```\n{error[:500]}\n```",
                    ),
                    chat_id=chat_id,
                )
            elif channel == "teams":
                await self._notify_teams("send_error", run_id, error, chat_id)


# 单例
notifier = Notifier()
