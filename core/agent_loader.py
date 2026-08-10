"""Agent Loader — Reads agent.yaml and prompt.md to build agent configurations."""

import yaml
import os
from typing import Optional


class AgentLoader:
    AGENT_BASE_PATH = "agents"

    def load(self, agent_name: str) -> dict:
        for root, dirs, _ in os.walk(self.AGENT_BASE_PATH):
            if os.path.basename(root) == agent_name:
                return self._load_from_dir(root)

        raise FileNotFoundError(f"Agent '{agent_name}' not found under {self.AGENT_BASE_PATH}")

    def _load_from_dir(self, dir_path: str) -> dict:
        yaml_path = os.path.join(dir_path, "agent.yaml")
        prompt_path = os.path.join(dir_path, "prompt.md")

        with open(yaml_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        if os.path.exists(prompt_path):
            with open(prompt_path, "r", encoding="utf-8") as f:
                config["system_prompt"] = f.read()

        return config

    def list_all(self) -> list:
        agents = []
        for root, dirs, _ in os.walk(self.AGENT_BASE_PATH):
            if "agent.yaml" in os.listdir(root):
                agents.append(os.path.basename(root))
        return agents

    def get_subagent_names(self) -> list:
        """Return only pipeline subagents."""
        path = os.path.join(self.AGENT_BASE_PATH, "subagents")
        if os.path.exists(path):
            return [d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))]
        return []

    def get_independent_names(self) -> list:
        """Return only independent agents."""
        path = os.path.join(self.AGENT_BASE_PATH, "independent")
        if os.path.exists(path):
            return [d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))]
        return []
