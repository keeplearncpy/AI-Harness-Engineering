"""
Harness Engine — Pydantic Data Models.
"""

from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field


# ================================================================
# Conversation / Clarification
# ================================================================

class ConversationState(str, Enum):
    CLARIFYING = "clarifying"       # Asking follow-up questions
    CONFIRMED = "confirmed"         # Requirements confirmed
    RUNNING = "running"             # Pipeline executing
    WAITING_APPROVAL = "waiting_approval"  # CI/CD manual approval
    COMPLETED = "completed"
    FAILED = "failed"


class ClarificationRound(BaseModel):
    """One round of clarification Q&A."""
    round: int = 1
    question: str          # Engine/agent asks user
    answer: str = ""       # User's Teams reply
    recorded_in_task: bool = False  # Saved to Yunxiao task


class ConversationContext(BaseModel):
    """Tracks the ongoing clarification conversation."""
    run_id: str
    state: ConversationState = ConversationState.CLARIFYING
    original_message: str           # What the user initially asked
    yunxiao_task_id: str = ""       # Yunxiao task/story ID
    yunxiao_task_url: str = ""      # Link to the task
    rounds: list[ClarificationRound] = Field(default_factory=list)
    confirmed_requirements: str = ""  # Final confirmed requirements
    max_rounds: int = 10
    teams_channel_id: str = ""
    teams_user: str = ""


# ================================================================
# Teams Webhook
# ================================================================

class TeamsWebhookPayload(BaseModel):
    text: str = ""                          # Raw message text
    user: str = "unknown"
    channel_id: str = ""
    channel_name: str = ""
    conversation_id: str = ""               # Teams thread ID
    reply_to_run_id: str = ""               # If replying to an existing conversation
    command: str = ""                       # /harness-new, /harness-iterate
    description: str = ""


# ================================================================
# Pipeline Trigger
# ================================================================

class PipelineTriggerRequest(BaseModel):
    workflow: str = "new_project"
    description: str
    options: dict = Field(default_factory=dict)


# ================================================================
# Phase Status
# ================================================================

class PhaseStatus(BaseModel):
    phase_name: str = ""
    status: str = "pending"      # pending, running, completed, failed, skipped
    agent: str = ""              # e.g., harness-fsd
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result_summary: str = ""     # Brief output summary
    output_path: str = ""        # Output file paths


# ================================================================
# Pipeline State
# ================================================================

class PipelineState(BaseModel):
    run_id: str
    project_name: str = ""
    workflow: str = "new_project"
    current_phase: int = 0
    total_phases: int = 6        # clarify → fsd → data → code → test → review → approval
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
# Observability
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
# Health
# ================================================================

class HealthResponse(BaseModel):
    status: str
    version: str
    opencode_connected: bool = False
