"""
Harness Engine — Pydantic 数据模型。
"""

from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field


# ================================================================
# 对话 / 需求澄清
# ================================================================

class ConversationState(str, Enum):
    CLARIFYING = "clarifying"       # 正在追问澄清问题
    CONFIRMED = "confirmed"         # 需求已确认
    RUNNING = "running"             # 流水线执行中
    WAITING_APPROVAL = "waiting_approval"  # 等待 CI/CD 人工审批
    COMPLETED = "completed"
    FAILED = "failed"


class ClarificationRound(BaseModel):
    """一轮澄清问答。"""
    round: int = 1
    question: str          # 引擎/agent 向用户提问
    answer: str = ""       # 用户在聊天平台的回复
    recorded_in_task: bool = False  # 是否已记录到云效任务


class ConversationContext(BaseModel):
    """跟踪进行中的澄清对话。"""
    run_id: str
    state: ConversationState = ConversationState.CLARIFYING
    original_message: str           # 用户最初的请求
    yunxiao_task_id: str = ""       # 云效任务/需求 ID
    yunxiao_task_url: str = ""      # 任务链接
    rounds: list[ClarificationRound] = Field(default_factory=list)
    confirmed_requirements: str = ""  # 最终确认的需求
    max_rounds: int = 10
    # 消息来源平台（"lark" | "teams" | ...），
    # 用于路由回复以及关联同一会话的后续消息
    platform: str = "lark"
    platform_chat_id: str = ""
    # 处理该会话的 agent（多机器人时由应用配置决定）
    agent: str = "harness-yunxiao-agent"
    teams_channel_id: str = ""
    teams_user: str = ""


# ================================================================
# Teams Webhook
# ================================================================

class TeamsWebhookPayload(BaseModel):
    text: str = ""                          # 原始消息文本
    user: str = "unknown"
    channel_id: str = ""
    channel_name: str = ""
    conversation_id: str = ""               # Teams 线程 ID
    reply_to_run_id: str = ""               # 回复已有会话时携带
    command: str = ""                       # /harness-new、/harness-iterate
    description: str = ""


# ================================================================
# 流水线触发
# ================================================================

class PipelineTriggerRequest(BaseModel):
    workflow: str = "new_project"
    description: str
    options: dict = Field(default_factory=dict)


# ================================================================
# 阶段状态
# ================================================================

class PhaseStatus(BaseModel):
    phase_name: str = ""
    status: str = "pending"      # pending, running, completed, failed, skipped
    agent: str = ""              # 如 harness-fsd
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result_summary: str = ""     # 阶段输出摘要
    output_path: str = ""        # 输出文件路径


# ================================================================
# 流水线状态
# ================================================================

class PipelineState(BaseModel):
    run_id: str
    project_name: str = ""
    workflow: str = "new_project"
    current_phase: int = 0
    total_phases: int = 6        # 澄清 → FSD → 数据 → 代码 → 测试 → 评审 → 审批
    status: str = "pending"
    session_id: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    phases: list[PhaseStatus] = Field(default_factory=list)
    conversation: Optional[ConversationContext] = None


class PipelineStatusResponse(BaseModel):
    run_id: str
    project: str
    current_phase: int
    total_phases: int
    status: str
    conversation_state: Optional[str] = None
    phases: list[PhaseStatus] = Field(default_factory=list)


# ================================================================
# 可观测性
# ================================================================

class AgentExecutionRecord(BaseModel):
    run_id: str
    agent: str
    phase: str
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    duration_ms: int = 0
    status: str = "unknown"
    token_usage: dict = Field(default_factory=dict)
    retry_count: int = 0
    error_message: Optional[str] = None


# ================================================================
# 健康检查
# ================================================================

class HealthResponse(BaseModel):
    status: str
    version: str
    opencode_connected: bool = False
