"""
Harness Engine — 可观测性。
跟踪 agent 执行指标、校验产出、生成仪表盘。

输出位置：所创建项目的 docs/observability/ 目录（每次会话一组报告）。
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
    """旁路可观测性：跟踪、校验、报告。"""

    def __init__(self, project_root: str = None):
        if project_root:
            path = Path(project_root)
        else:
            # 引擎模式下项目根目录 = 进程工作目录（fsd/、design/ 等产物所在处）
            path = Path.cwd()
        self._report_dir = path / "docs" / "observability"
        self._report_dir.mkdir(parents=True, exist_ok=True)

        self._records: dict[str, list[AgentExecutionRecord]] = {}

    # ===============================================================
    # 运行生命周期
    # ===============================================================

    async def start_run(self, state: PipelineState):
        self._records[state.run_id] = []
        log.info(f"可观测性: 开始运行 {state.run_id}")

    async def end_run(self, state: PipelineState):
        records = self._records.get(state.run_id, [])
        self._persist_log(state.run_id, records)
        self._generate_dashboard(state.run_id, state, records)
        self._update_index(state.run_id, state)
        log.info(f"可观测性: 结束运行 {state.run_id}（{len(records)} 条记录）"
                 f" → docs/observability/")

    # ===============================================================
    # 阶段记录
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
            token_usage=token_usage or {},
        )
        if run_id not in self._records:
            self._records[run_id] = []
        self._records[run_id].append(record)

    # ===============================================================
    # 持久化
    # ===============================================================

    def _persist_log(self, run_id: str, records: list[AgentExecutionRecord]):
        filepath = self._report_dir / f"execution-{run_id}.jsonl"
        with open(filepath, "w", encoding="utf-8") as f:
            for r in records:
                f.write(r.model_dump_json() + "\n")

    # ===============================================================
    # 仪表盘生成
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
        filepath = self._report_dir / f"dashboard-{run_id}.md"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(dashboard)

    def _update_index(self, run_id: str, state: PipelineState):
        """追加/更新 docs/observability/INDEX.md 会话索引。"""
        index_path = self._report_dir / "INDEX.md"
        entry = (
            f"| {run_id} | {state.project_name} | {state.status} | "
            f"{state.started_at or ''} | "
            f"[summary](summary-{run_id}.md) / [dashboard](dashboard-{run_id}.md) |"
        )
        header = (
            "| Run ID | Project | Status | Started | Reports |\n"
            "|--------|---------|--------|---------|---------|\n"
        )
        if index_path.exists():
            lines = index_path.read_text(encoding="utf-8").splitlines()
            lines = [l for l in lines if f"| {run_id} " not in l]
            lines.append(entry)
            index_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        else:
            index_path.write_text(
                "# Observability Index\n\n" + header + entry + "\n",
                encoding="utf-8",
            )

    # ===============================================================
    # 查询 API
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

        log_file = self._report_dir / f"execution-{run_id}.jsonl"
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
        filepath = self._report_dir / f"dashboard-{run_id}.md"
        if not filepath.exists():
            return None
        return filepath.read_text(encoding="utf-8")


observability = Observability()
