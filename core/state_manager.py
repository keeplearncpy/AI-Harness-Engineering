"""
Harness Engine — State Manager.
File-based persistence for pipeline state using JSON.
"""

import json
import logging
from pathlib import Path
from typing import Optional

from core.models import PipelineState

log = logging.getLogger("harness.state_manager")


class StateManager:
    """Manages pipeline state persistence."""

    def __init__(self, base_dir: str = None):
        if base_dir:
            path = Path(base_dir)
        else:
            path = Path(__file__).parent.parent / ".harness" / "states"
        self._dir = path
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, run_id: str) -> Path:
        return self._dir / f"{run_id}.json"

    def save(self, state: PipelineState):
        """Save pipeline state to disk."""
        filepath = self._path(state.run_id)
        data = state.model_dump(mode="json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        log.debug(f"State saved: {state.run_id} (phase {state.current_phase})")

    def get(self, run_id: str) -> Optional[PipelineState]:
        """Load pipeline state from disk."""
        filepath = self._path(run_id)
        if not filepath.exists():
            return None
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return PipelineState(**data)

    def list_all(self, limit: int = 50) -> list[PipelineState]:
        """List all saved pipeline states."""
        files = sorted(self._dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        states = []
        for fp in files[:limit]:
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    data = json.load(f)
                states.append(PipelineState(**data))
            except Exception as e:
                log.warning(f"Failed to load state {fp.name}: {e}")
        return states

    def delete(self, run_id: str):
        """Delete a pipeline state."""
        filepath = self._path(run_id)
        if filepath.exists():
            filepath.unlink()


state_manager = StateManager()
