"""Context Manager — Maintains project state and passes context between agents."""

import json
import os
from typing import Optional


class ContextManager:
    def __init__(self):
        self.project_state: dict = {}
        self.context_buffer: list = []

    def load_state(self, project_path: str) -> dict:
        state_file = os.path.join(project_path, ".harness_state.json")
        if os.path.exists(state_file):
            with open(state_file, "r", encoding="utf-8") as f:
                self.project_state = json.load(f)
        else:
            self.project_state = {
                "project_name": os.path.basename(project_path),
                "current_phase": 0,
                "phases": {}
            }
        return self.project_state

    def save_state(self, project_path: str):
        state_file = os.path.join(project_path, ".harness_state.json")
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(self.project_state, f, indent=2, ensure_ascii=False)

    def update_phase(self, phase_name: str, status: str, output: str = ""):
        self.project_state["phases"][phase_name] = {
            "status": status,
            "output": output,
            "completed_at": None
        }

    def get_context_summary(self, max_tokens: int = 4000) -> str:
        """Generate a compact summary for passing context to next agent."""
        return json.dumps(self.project_state, ensure_ascii=False)

    def push_to_buffer(self, message: str):
        self.context_buffer.append(message)

    def get_recent_context(self, n: int = 5) -> list:
        return self.context_buffer[-n:]
