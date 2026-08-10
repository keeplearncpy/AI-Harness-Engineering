"""Orchestrator — Main agent logic for intent recognition and workflow scheduling."""

import yaml
import os
from context_manager import ContextManager
from agent_loader import AgentLoader
from validator import Validator


class Orchestrator:
    def __init__(self, config_path: str = "config/settings.yaml"):
        self.config = self._load_config(config_path)
        self.context = ContextManager()
        self.loader = AgentLoader()
        self.validator = Validator()

    def _load_config(self, path: str) -> dict:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def run_new_project(self, user_query: str):
        workflow = self._load_workflow("new_project")
        print(f"[Orchestrator] Starting new project workflow...")
        # Phase execution logic would go here
        for phase in workflow.get("phases", []):
            self._execute_phase(phase)

    def run_iteration(self, user_query: str):
        workflow = self._load_workflow("iteration")
        print(f"[Orchestrator] Starting iteration workflow...")
        for phase in workflow.get("phases", []):
            self._execute_phase(phase)

    def _load_workflow(self, name: str) -> dict:
        path = f"config/workflows/{name}.yaml"
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _execute_phase(self, phase: dict):
        name = phase.get("name")
        agent_name = phase.get("agent")

        if agent_name:
            print(f"  [Phase] {name} — invoking agent: {agent_name}")
            agent_config = self.loader.load(agent_name)
            # Agent invocation with context would go here
        else:
            action = phase.get("action")
            print(f"  [Phase] {name} — action: {action}")

        self.validator.validate_phase_output(phase)
