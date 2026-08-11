"""
Harness Engine — FastAPI Webhook Server.
Receives Teams webhooks, routes to orchestrator, returns replies.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.config import settings
from core.models import (
    TeamsWebhookPayload,
    PipelineTriggerRequest,
    HealthResponse,
)
from core.orchestrator import orchestrator
from core.observability import observability
from core.opencode_client import opencode_client

log = logging.getLogger("harness.server")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info(f"Harness Engine starting on {settings.host}:{settings.port}")
    await orchestrator.start()
    yield
    await orchestrator.stop()
    log.info("Harness Engine stopped")


app = FastAPI(
    title="AI Harness Engineering Engine",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================================================================
# Health
# ================================================================

@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="ok",
        version="2.0.0",
        opencode_connected=await opencode_client.ping(),
    )


# ================================================================
# Teams Webhook — Primary Entry Point
# ================================================================

@app.post("/webhook/teams")
async def teams_webhook(request: Request):
    """
    Receive messages from Microsoft Teams via Power Automate.
    Routes to orchestrator for clarification loop or pipeline execution.
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Parse Teams message format (Power Automate may wrap it differently)
    text = body.get("text", "")
    # Support Power Automate Teams trigger format
    if "command" in body:
        text = body.get("command", "") + " " + body.get("description", "")
    elif "triggerBody" in body:
        inner = body["triggerBody"]
        text = inner.get("text", "") or inner.get("content", "")

    payload = TeamsWebhookPayload(
        text=text,
        user=body.get("user", body.get("from", {}).get("name", "unknown")),
        channel_id=body.get("channel_id", body.get("channel", {}).get("id", "")),
        channel_name=body.get("channel", {}).get("name", ""),
        conversation_id=body.get("conversation_id", body.get("conversation", {}).get("id", "")),
        reply_to_run_id=body.get("reply_to_run_id", body.get("run_id", "")),
    )

    log.info(f"Teams webhook: user={payload.user} text={payload.text[:100]}")

    result = await orchestrator.handle_teams_trigger(payload)
    return JSONResponse(result)


# ================================================================
# Pipeline Trigger — Programmatic API
# ================================================================

@app.post("/pipeline/trigger")
async def trigger_pipeline(req: PipelineTriggerRequest):
    log.info(f"Pipeline trigger: {req.workflow} — {req.description[:80]}")
    run_id = await orchestrator.new_project(req.description, req.options)
    return JSONResponse({"status": "started", "run_id": run_id})


# ================================================================
# Pipeline Status
# ================================================================

@app.get("/pipeline/{run_id}/status")
async def pipeline_status(run_id: str):
    state = await orchestrator.get_state(run_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")

    return JSONResponse({
        "run_id": state.run_id,
        "project": state.project_name,
        "current_phase": state.current_phase,
        "total_phases": state.total_phases,
        "status": state.status,
        "conversation_state": state.conversation.state.value if state.conversation else None,
        "phases": [p.model_dump(mode="json") for p in state.phases],
    })


# ================================================================
# Conversation Thread — View & Reply
# ================================================================

@app.get("/conversation/{run_id}")
async def get_conversation(run_id: str):
    """Get the full clarification conversation history."""
    import json
    from pathlib import Path
    path = Path(__file__).parent.parent / ".harness" / "conversations" / f"{run_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Conversation not found")
    with open(path, "r", encoding="utf-8") as f:
        return JSONResponse(json.load(f))


# ================================================================
# Observability
# ================================================================

@app.get("/observability/runs")
async def list_runs(limit: int = 20):
    return JSONResponse(await observability.list_runs(limit))


@app.get("/observability/run/{run_id}")
async def run_detail(run_id: str):
    detail = await observability.get_run_detail(run_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return JSONResponse(detail)


@app.get("/observability/dashboard/{run_id}")
async def run_dashboard(run_id: str):
    dashboard = await observability.get_dashboard(run_id)
    if dashboard is None:
        raise HTTPException(status_code=404, detail="Dashboard not yet generated")
    return JSONResponse({"markdown": dashboard})


# ================================================================
# Approval Webhook (Power Automate)
# ================================================================

@app.post("/webhook/approval")
async def approval_webhook(request: Request):
    body = await request.json()
    log.info(f"Approval webhook: run={body.get('run_id')} approved={body.get('approved')}")
    await orchestrator.handle_approval(body)
    return JSONResponse({"status": "ok"})
