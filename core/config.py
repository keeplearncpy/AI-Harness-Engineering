"""
Harness Engine — Configuration.
"""

import os
from pathlib import Path


class Settings:
    # -----------------------------------------------------------
    # Server
    # -----------------------------------------------------------
    host: str = os.getenv("HARNESS_HOST", "0.0.0.0")
    port: int = int(os.getenv("HARNESS_PORT", "8000"))

    # -----------------------------------------------------------
    # OpenCode Connection
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
    # Defaults
    # -----------------------------------------------------------
    default_model: str = os.getenv("HARNESS_MODEL", "qwen3.7-max")
    max_clarification_rounds: int = int(os.getenv("HARNESS_MAX_CLARIFY", "10"))

    @property
    def teams_configured(self) -> bool:
        return bool(self.teams_webhook_url)


settings = Settings()

# Ensure data dirs exist
for sub in ["logs", "dashboards", "states", "conversations"]:
    (Path(__file__).parent.parent / ".harness" / sub).mkdir(parents=True, exist_ok=True)
