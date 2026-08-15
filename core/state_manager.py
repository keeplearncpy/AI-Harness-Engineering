"""
Harness Engine — 状态管理器。
基于 JSON 文件的流水线状态持久化。
"""

import json
import logging
from pathlib import Path
from typing import Optional

from core.models import PipelineState, ConversationState

log = logging.getLogger("harness.state_manager")


class StateManager:
    """管理流水线状态的持久化。"""

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
        """保存流水线状态到磁盘。"""
        filepath = self._path(state.run_id)
        data = state.model_dump(mode="json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        log.debug(f"状态已保存: {state.run_id} (阶段 {state.current_phase})")

    def get(self, run_id: str) -> Optional[PipelineState]:
        """从磁盘加载流水线状态。"""
        filepath = self._path(run_id)
        if not filepath.exists():
            return None
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return PipelineState(**data)

    def list_all(self, limit: int = 50) -> list[PipelineState]:
        """列出所有已保存的流水线状态（按修改时间倒序）。"""
        files = sorted(self._dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        states = []
        for fp in files[:limit]:
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    data = json.load(f)
                states.append(PipelineState(**data))
            except Exception as e:
                log.warning(f"加载状态失败 {fp.name}: {e}")
        return states

    def delete(self, run_id: str):
        """删除一个流水线状态。"""
        filepath = self._path(run_id)
        if filepath.exists():
            filepath.unlink()

    def find_by_chat(self, platform: str, chat_id: str) -> Optional[PipelineState]:
        """
        按平台会话查找最近的活动对话。
        用于关联不带 run_id 的后续消息（如澄清回答）。
        """
        active_states = {ConversationState.CLARIFYING, ConversationState.WAITING_APPROVAL}
        for state in self.list_all(limit=100):
            conv = state.conversation
            if conv is None or conv.state not in active_states:
                continue
            if conv.platform == platform and conv.platform_chat_id == chat_id:
                return state
        return None


state_manager = StateManager()
