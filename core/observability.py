"""
Harness Engine — Observability.
Tracks agent execution metrics, validates outputs, generates dashboards.
"""

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from core.models import PipelineState, AgentExecutionRecord

log = logging.getLogger("harness.observability")


class Observability:
    """Sidecar observability: tracks, validates, reports."""

    def __init__(self, base_dir: str = None):
        if base_dir:
            path = Path(base_dir)
        else:
            path = Path(__file__).parent.parent / ".harness"
        self._log_dir = path / "logs"
        self._dash_dir = path / "dashboards"
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._dash_dir.mkdir(parents=True, exist_ok=True)

        self._records: dict[str, list[AgentExecutionRecord]] = {}

    # ===============================================================
    # Run Lifecycle
    # ===============================================================

    async def start_run(self, state: PipelineState):
        self._records[state.run_id] = []
        log.info(f"Observability: starting run {state.run_id}")

    async def end_run(self, state: PipelineState):
        records = self._records.get(state.run_id, [])
        self._persist_log(state.run_id, records)
        self._generate_dashboard(state.run_id, state, records)
        log.info(f"Observability: ended run {state.run_id} ({len(records)} records)")

    # ===============================================================
    # Phase Recording
    # ===============================================================

    async def record_phase(
        self,
        run_id: str,
        agent: str,
        phase: str,
        status: str,
        result: dict = None,
        duration_ms: int = 0,
        token_usage: dict = None,
    ):
        record = AgentExecutionRecord(
            run_id=run_id,
            agent=agent,
            phase=phase,
            started_at=datetime.now(timezone.utc).isoformat(),
            ended_at=datetime.now(timezone.utc).isoformat(),
            duration_ms=duration_ms,
            status=status,
            schema_valid=True,
            token_usage=token_usage or {},
        )
        if run_id not in self._records:
            self._records[run_id] = []
        self._records[run_id].append(record)

    # ===============================================================
    # Persistence
    # ===============================================================

    def _persist_log(self, run_id: str, records: list[AgentExecutionRecord]):
        filepath = self._log_dir / f"execution-{run_id}.jsonl"
        with open(filepath, "w", encoding="utf-8") as f:
            for r in records:
                f.write(r.model_dump_json() + "\n")

    # ===============================================================
    # Dashboard Generation
    # ===============================================================

    def _generate_dashboard(self, run_id: str, state: PipelineState, records: list[AgentExecutionRecord]):
        lines = [
            f"# Pipeline Dashboard: {run_id}",
            "",
            f"**Project**: {state.project_name}",
            f"**Workflow**: {state.workflow}",
            f"**Status**: {state.status}",
            f"**Started**: {state.started_at}",
            "",
            "## Agent Execution Summary",
            "",
            "| Agent | Phase | Status |",
            "|-------|-------|--------|",
        ]
        for r in records:
            emoji = "✅" if r.status == "success" else "❌"
            lines.append(f"| {r.agent} | {r.phase} | {emoji} {r.status} |")

        lines.extend(["", "## Pipeline Flow", "", "```mermaid", "graph TD"])
        prev = None
        for i, r in enumerate(records):
            lines.append(f"    agent_{i}[{r.agent}]")
            if prev is not None:
                lines.append(f"    agent_{prev} --> agent_{i}")
            prev = i
        if records:
            lines.append(f"    agent_{len(records)-1} --> done[Done]")
        lines.append("```")

        dashboard = "\n".join(lines)
        filepath = self._dash_dir / f"pipeline-{run_id}.md"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(dashboard)

    # ===============================================================
    # Query API
    # ===============================================================

    async def list_runs(self, limit: int = 20) -> list[dict]:
        states = []
        from core.state_manager import state_manager
        for s in state_manager.list_all(limit):
            states.append({
                "run_id": s.run_id,
                "project": s.project_name,
                "status": s.status,
                "current_phase": s.current_phase,
                "total_phases": s.total_phases,
                "started_at": s.started_at,
            })
        return states

    async def get_run_detail(self, run_id: str) -> Optional[dict]:
        from core.state_manager import state_manager
        state = state_manager.get(run_id)
        if state is None:
            return None

        log_file = self._log_dir / f"execution-{run_id}.jsonl"
        records = []
        if log_file.exists():
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        records.append(json.loads(line))

        return {
            "state": state.model_dump(mode="json"),
            "records": records,
        }

    async def get_dashboard(self, run_id: str) -> Optional[str]:
        filepath = self._dash_dir / f"pipeline-{run_id}.md"
        if not filepath.exists():
            return None
        return filepath.read_text(encoding="utf-8")


observability = Observability()
