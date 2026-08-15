"""
Harness Engine — 配置中心。
"""

import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

# 从项目根目录（core/ 的上级）加载 .env
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# 让 harness 相关日志可见（uvicorn 保持自己的日志配置）
logging.basicConfig(
    level=os.getenv("HARNESS_LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logging.getLogger("harness").setLevel(os.getenv("HARNESS_LOG_LEVEL", "INFO"))


class Settings:
    # -----------------------------------------------------------
    # 服务端
    # -----------------------------------------------------------
    host: str = os.getenv("HARNESS_HOST", "0.0.0.0")
    port: int = int(os.getenv("HARNESS_PORT", "8000"))

    # -----------------------------------------------------------
    # OpenCode 连接
    # -----------------------------------------------------------
    opencode_host: str = os.getenv("OPENCODE_HOST", "127.0.0.1")
    opencode_port: int = int(os.getenv("OPENCODE_PORT", "4096"))
    opencode_timeout: int = int(os.getenv("OPENCODE_TIMEOUT", "300"))

    # -----------------------------------------------------------
    # Teams
    # -----------------------------------------------------------
    teams_webhook_url: str = os.getenv("TEAMS_WEBHOOK_URL", "")
    teams_app_id: str = os.getenv("TEAMS_APP_ID", "")

    # -----------------------------------------------------------
    # Power Automate
    # -----------------------------------------------------------
    power_automate_flow_approval: str = os.getenv("POWER_AUTOMATE_FLOW_APPROVAL", "")

    # -----------------------------------------------------------
    # 飞书（Lark）多应用配置
    #
    # 支持多个飞书机器人：一个机器人绑定一个 agent。
    # 优先使用 LARK_APPS_JSON（JSON 数组）；未配置时回退到
    # 单应用环境变量 LARK_APP_ID / LARK_APP_SECRET。
    #
    # LARK_APPS_JSON 格式：
    # [
    #   {
    #     "name": "yunxiao-bot",            # 应用名（webhook URL /{name} 使用）
    #     "app_id": "cli_xxx",
    #     "app_secret": "yyy",
    #     "agent": "harness-yunxiao-agent"  # 该机器人绑定的 agent
    #   }
    # ]
    # -----------------------------------------------------------
    lark_apps_json: str = os.getenv("LARK_APPS_JSON", "")
    lark_app_id: str = os.getenv("LARK_APP_ID", "")
    lark_app_secret: str = os.getenv("LARK_APP_SECRET", "")
    lark_verification_token: str = os.getenv("LARK_VERIFICATION_TOKEN", "")
    lark_encrypt_key: str = os.getenv("LARK_ENCRYPT_KEY", "")
    # 事件接入模式："webhook"（事件订阅）或 "websocket"（长连接）
    lark_event_mode: str = os.getenv("LARK_EVENT_MODE", "webhook")
    # 飞书（open.feishu.cn）或 Lark 国际版（open.larksuite.com）
    lark_domain: str = os.getenv("LARK_DOMAIN", "https://open.feishu.cn")

    # -----------------------------------------------------------
    # 默认值
    # -----------------------------------------------------------
    default_model: str = os.getenv("HARNESS_MODEL", "qwen3.7-max")
    max_clarification_rounds: int = int(os.getenv("HARNESS_MAX_CLARIFY", "10"))

    # agent 角色 → 实际 agent 名 的映射（JSON），
    # 用于适配当前 opencode 实例实际加载的 agent。
    # 默认映射到 opencode 内置/通用 agent，无需额外安装。
    agent_map_json: str = os.getenv("HARNESS_AGENT_MAP", "")

    # -----------------------------------------------------------
    # 派生属性
    # -----------------------------------------------------------

    @property
    def lark_apps(self) -> list[dict]:
        """所有飞书应用配置（多机器人），未配置时返回空列表。"""
        if self.lark_apps_json:
            try:
                apps = json.loads(self.lark_apps_json)
                if isinstance(apps, list):
                    return [a for a in apps if isinstance(a, dict)
                            and a.get("app_id") and a.get("app_secret")]
            except Exception as e:
                logging.getLogger("harness.config").error(f"LARK_APPS_JSON 解析失败: {e}")
        # 单应用回退
        if self.lark_app_id and self.lark_app_secret:
            return [{
                "name": "lark",
                "app_id": self.lark_app_id,
                "app_secret": self.lark_app_secret,
                "agent": "",
            }]
        return []

    @property
    def teams_configured(self) -> bool:
        return bool(self.teams_webhook_url)

    @property
    def lark_configured(self) -> bool:
        return bool(self.lark_apps)

    @property
    def agent_map(self) -> dict:
        """
        agent 角色 → 实际 agent 名 的映射。
        默认指向 opencode 内置/通用 agent（无需安装 harness-* 插件），
        可通过 HARNESS_AGENT_MAP（JSON）覆盖。
        """
        default_map = {
            "chat": "build",                # 闲聊/问答（主 agent，回复质量最高）
            "clarify": "general",           # 澄清 / 云效任务（原 harness-yunxiao-agent）
            "fsd": "fsd_generator",         # 功能规格文档（原 harness-fsd）
            "data_modeler": "data_modeler",
            "backend_dev": "backend_dev",
            "frontend_dev": "frontend_dev",
            "tester": "tester",
            "reviewer": "code-reviewer",
        }
        if self.agent_map_json:
            try:
                custom = json.loads(self.agent_map_json)
                if isinstance(custom, dict):
                    default_map.update(custom)
            except Exception as e:
                logging.getLogger("harness.config").error(f"HARNESS_AGENT_MAP 解析失败: {e}")
        return default_map


settings = Settings()

# 确保数据目录存在
for sub in ["logs", "dashboards", "states", "conversations"]:
    (Path(__file__).parent.parent / ".harness" / sub).mkdir(parents=True, exist_ok=True)
