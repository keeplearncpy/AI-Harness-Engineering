"""
Harness Engine — FastAPI Webhook 服务。
通过消息接入层接收各聊天平台（Teams、飞书等）的消息，
路由到编排器，并返回回复。
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
from core.messaging import message_router

log = logging.getLogger("harness.server")

_listener_tasks = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info(f"Harness Engine 启动于 {settings.host}:{settings.port}")
    await orchestrator.start()

    # 绑定卡片按钮回调（飞书 CI/CD 审批）
    message_router.bind_card_actions(orchestrator.handle_card_action)

    # 启动主动消息接入（如飞书长连接），多机器人时每个应用各一条连接
    _listener_tasks.extend(
        await message_router.start_listeners(orchestrator.handle_message)
    )

    yield

    await message_router.stop_listeners(_listener_tasks)
    await orchestrator.stop()
    log.info("Harness Engine 已停止")


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
# 健康检查
# ================================================================

@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="ok",
        version="2.0.0",
        opencode_connected=await opencode_client.ping(),
    )


# ================================================================
# Teams Webhook — 主入口之一
# ================================================================

@app.post("/webhook/teams")
async def teams_webhook(request: Request):
    """
    通过 Power Automate 接收 Microsoft Teams 消息。
    路由到编排器进行澄清循环或流水线执行。
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # 解析 Teams 消息格式（Power Automate 可能有不同包装）
    text = body.get("text", "")
    # 兼容 Power Automate Teams 触发器格式
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
# 飞书 Webhook — 事件订阅模式
# ================================================================

@app.post("/webhook/lark")
async def lark_webhook(request: Request):
    """
    接收飞书应用事件（单机器人场景）。
    处理 URL 验证（challenge）、事件加密与 im.message.receive_v1 事件。
    """
    result = await message_router.handle_webhook("lark", request)
    return JSONResponse(result.body, status_code=result.status_code)


@app.post("/webhook/lark/{app_name}")
async def lark_app_webhook(app_name: str, request: Request):
    """
    接收指定飞书应用的事件（多机器人场景）。
    每个飞书应用在开发者后台配置不同的请求地址：
      /webhook/lark/<应用名>
    """
    result = await message_router.handle_webhook("lark", request, name=app_name)
    return JSONResponse(result.body, status_code=result.status_code)


# ================================================================
# 通用平台 Webhook — 任意注册进路由器的适配器
# ================================================================

@app.post("/webhook/message/{platform}")
async def platform_webhook(platform: str, request: Request):
    """所有已注册聊天平台的统一 webhook 入口（单实例平台）。"""
    result = await message_router.handle_webhook(platform, request)
    return JSONResponse(result.body, status_code=result.status_code)


@app.post("/webhook/message/{platform}/{app_name}")
async def platform_app_webhook(platform: str, app_name: str, request: Request):
    """统一 webhook 入口（指定应用实例）。"""
    result = await message_router.handle_webhook(platform, request, name=app_name)
    return JSONResponse(result.body, status_code=result.status_code)


# ================================================================
# 流水线触发 — 编程接口
# ================================================================

@app.post("/pipeline/trigger")
async def trigger_pipeline(req: PipelineTriggerRequest):
    log.info(f"流水线触发: {req.workflow} — {req.description[:80]}")
    run_id = await orchestrator.new_project(req.description, req.options)
    return JSONResponse({"status": "started", "run_id": run_id})


# ================================================================
# 流水线状态
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
# 对话线程 — 查看与回复
# ================================================================

@app.get("/conversation/{run_id}")
async def get_conversation(run_id: str):
    """获取完整的澄清对话历史。"""
    import json
    from pathlib import Path
    path = Path(__file__).parent.parent / ".harness" / "conversations" / f"{run_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Conversation not found")
    with open(path, "r", encoding="utf-8") as f:
        return JSONResponse(json.load(f))


# ================================================================
# 可观测性
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
# 审批 Webhook（Power Automate）
# ================================================================

@app.post("/webhook/approval")
async def approval_webhook(request: Request):
    body = await request.json()
    log.info(f"审批 webhook: run={body.get('run_id')} approved={body.get('approved')}")
    await orchestrator.handle_approval(body)
    return JSONResponse({"status": "ok"})
