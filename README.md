# AI Harness Engineering

AI-powered full-stack project scaffolding and iteration platform.

**双重身份 / Dual-Mode**:
1. **本地工具包** — `install.sh` 一键安装 agents/skills/commands 到 OpenCode；
   本地 `/harness-new`、`/harness-iterate` 命令即触发完整工作流（主 agent 扮演编排器）
2. **Agent Loop 引擎** — 自身是一个运行中的编排引擎，连接飞书（默认）/ Teams → Power Automate → 云效 → OpenCode，实现全流程自动化

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt
npm install

# 2. Configure environment
cp .env.example .env
# Edit .env with your credentials

# 3. Start OpenCode server (in one terminal)
opencode serve --port 4096

# 4. Start Harness Engine (in another terminal)
python core/main.py

# 5. Install agents/skills/commands to local OpenCode
./install.sh
```

### Mode 1: 本地 OpenCode 工作流（不走引擎）

安装后，在任何项目里启动 `opencode`，直接使用：

```bash
/harness-new <项目描述>      # 本地全流程：FSD → 原型/数据建模 → 前后端 → 测试 → 评审
/harness-iterate <变更描述>  # 本地增量：新功能 / bug 修复 / 重构
```

命令注入后主 agent 自动扮演编排器，按阶段调用子代理完成整个工作流。
（子代理按 `~/.config/opencode/agents/` 中的 harness-* 加载，无需引擎）

The engine listens on `http://localhost:8000` for:
- **Teams webhook** → `POST /webhook/teams`
- **Pipeline API** → `POST /pipeline/trigger`
- **Observability** → `GET /observability/runs`
- **Health** → `GET /health`

---

## Architecture

```
                    ┌─────────────────────────────────────────┐
                    │   聊天平台（飞书默认，可配 Teams 等）      │
                    │   飞书: websocket/webhook → /webhook/lark  │
                    │   Teams: Power Automate → /webhook/teams   │
                    └─────────────────┬───────────────────────┘
                                      │
    ┌─────────────────────────────────▼────────────────────────────┐
    │                    Harness Engine (core/)                     │
    │                                                              │
    │  ┌──────────┐   ┌──────────────┐   ┌──────────────────┐     │
    │  │ server.py│   │ orchestrator │   │ observability.py │     │
    │  │ (FastAPI)│──▶│   .py        │──▶│ (sidecar)        │     │
    │  └──────────┘   └──────┬───────┘   └──────────────────┘     │
    │                        │                                      │
    │         ┌──────────────┼──────────────┐                      │
    │         ▼              ▼              ▼                      │
    │  ┌────────────┐ ┌────────────┐ ┌────────────┐               │
    │  │ opencode   │ │  teams     │ │ state      │               │
    │  │ _client.py │ │ _notifier  │ │ _manager   │               │
    │  └─────┬──────┘ └────────────┘ └────────────┘               │
    └────────┼────────────────────────────────────────────────────┘
             │
    ┌────────▼──────────────────────────────────────┐
    │  OpenCode Server (localhost:4096)              │
    │  ┌──────────────────────────────────────────┐ │
    │  │  Yunxiao MCP Server                      │ │
    │  │  └─ Projex tasks / Codeup / Flow / ACK   │ │
    │  │  Agents: harness-fsd, data-modeler, ...  │ │
    │  │  Skills: SKILL.md + templates + refs     │ │
    │  └──────────────────────────────────────────┘ │
    └──────────────────────────────────────────────┘
```

## Project Structure

```
ai-harness-engineering/
├── README.md
├── opencode.json              # Self-referential config
├── install.sh                 # One-click install to ~/.config/opencode/
├── requirements.txt           # Python dependencies (engine)
├── package.json               # Node dependencies (OpenCode SDK)
├── .env.example               # Environment configuration template
├── AGENTS.md                  # OpenCode project context
│
├── core/                      # Engine Layer — the actual running service
│   ├── server.py              # FastAPI webhook receiver + API
│   ├── orchestrator.py        # Pipeline engine + clarification loop
│   ├── opencode_client.py     # OpenCode HTTP API wrapper
│   ├── teams_notifier.py      # Teams Adaptive Card notifications
│   ├── state_manager.py       # Pipeline state persistence
│   ├── observability.py       # Metrics, dashboards (sidecar)
│   ├── models.py              # Pydantic data models
│   ├── config.py              # Configuration loader
│   ├── main.py                # Entry point (python core/main.py)
│   └── __init__.py
│
├── skills/                    # Skill Layer — knowledge packs
│   ├── harness-fsd/           # Requirements → FSD
│   ├── harness-prototype/     # FSD → HTML wireframe prototype
│   ├── harness-data-model/    # FSD → DB Schema
│   ├── harness-frontend/      # FSD + Prototype + Schema → 前端代码（技术栈随 SSD 动态）
│   ├── harness-backend/       # FSD + Schema → 后端代码（技术栈随 SSD 动态）
│   ├── harness-testing/       # Code + FSD → Tests
│   ├── harness-code-review/   # Code → Review Report
│   ├── harness-zentao-agent/  # Zentao PMS Integration
│   ├── harness-observability/ # Monitor & visualize
│   └── harness-teams/         # Teams + Power Automate
│
├── agents/                    # Agent Layer — YAML frontmatter (.md)
│   ├── harness-orchestrator.md
│   ├── harness-fsd.md
│   ├── harness-prototype.md
│   ├── harness-data-modeler.md
│   ├── harness-frontend-dev.md
│   ├── harness-backend-dev.md
│   ├── harness-tester.md
│   ├── harness-reviewer.md
│   ├── harness-zentao-agent.md
│   ├── harness-yunxiao-agent.md
│   ├── harness-teams-agent.md
│   └── harness-observability.md
│
└── commands/                  # Shortcut commands（工作流入口）
    ├── harness-new.md         # /harness-new — 本地全流程工作流
    └── harness-iterate.md     # /harness-iterate — 本地增量工作流
    # install.sh 会同步安装到 ~/.config/opencode/command/；
    # 本仓库 .opencode/command/ 下有同名副本（仓库内直接可用）
```

## How It Actually Works

### 1. 聊天平台对话 → Clarification Loop

```
用户在飞书（默认）/ Teams 中发消息: "帮我做一个库存管理系统"
    │
    ▼
飞书: websocket 长连接 / webhook 事件订阅 → Engine
Teams: Power Automate → HTTP POST → Engine :8000/webhook/teams
    │
    ▼
Engine → OpenCode → yunxiao-agent (MCP)
    │   └── 创建云效任务
    │   └── 分析需求是否清晰
    │
    ├── 需求不清晰: "QUESTION: 需要管理哪些类型的库存？原材料、半成品还是成品？"
    │       │
    │       ▼
    │   聊天平台回复: "主要是成品库存管理"
    │       │
    │       ▼
    │   Engine → yunxiao-agent → 更新任务 → 继续追问
    │       │
    │       ├── "QUESTION: 是否需要支持多仓库管理和库位追踪？"
    │       │
    │       └── ... 最多10轮追问，直到需求确认
    │
    └── 需求确认: "CONFIRMED: 成品库存管理系统，支持多仓库、库位追踪、出入库..."
            │
            ▼
        所有对话记录已存入云效任务 ←── yunxiao-agent (MCP)
```

### 2. Pipeline Execution

```
Phase 0: 需求澄清 ──→ Teams追问循环, 记录存云效
Phase 1: FSD 生成   ──→ harness-fsd → fsd/SSD-SystemOverview.md（含「技术选型」章节）
                      + fsd/{模块}/feature-{功能名}-{索引}.md（bug 修复为 fix-bug-{修复名}-{索引}.md）
                      ★ 技术栈由 FSD 阶段确定并写入 SSD，下游不再写死技术栈
Phase 2: 原型+建模 ──→ harness-prototype | harness-data-modeler (并行)
                      prototype/ HTML 线框 + click-map.md（页面/路由/菜单/按钮/表单点击关系）
                      design/db-schema.sql（DDL 方言按 SSD 技术选型）
Phase 3: 代码生成   ──→ harness-frontend-dev | harness-backend-dev
                      （技术栈动态注入：project_context.tech_stack > SSD 技术选型 > 默认兜底）
Phase 4: 测试       ──→ harness-tester → tests/
Phase 5: 代码评审   ──→ harness-reviewer → reviews/
Phase 6: CI/CD审批  ──→ 审批卡片（默认飞书消息审批，卡片按钮 批准/拒绝）
                      NOTIFY_CHANNEL 可配置: feishu(默认) | teams | both | none
     │
     ├── ✅ 批准 → yunxiao-agent 触发 Flow 流水线 → 部署到 ACK
     └── ❌ 拒绝 → 停止流水线, 通知请求会话
```

### 3. 全程可观测

每次会话结束自动生成一组可观测性报告，输出到**所创建项目的 `docs/observability/`** 目录：

- `summary-{run_id}.md` — 会话总结（阶段完成情况、产物统计、问题清单）
- `dashboard-{run_id}.md` — 仪表盘（Mermaid 流程图 + 统计表）
- `execution-{run_id}.jsonl` — 逐阶段执行记录（append-only）
- `INDEX.md` — 所有会话报告的索引

本地模式由 `/harness-new`、`/harness-iterate` 的最后一个阶段触发（扫描项目目录收集数据）；
引擎模式作为 sidecar 自动执行。每次会话生成一份，互不覆盖。

### 4. CLI 直接触发 (不走 Teams)

```bash
curl -X POST http://localhost:8000/pipeline/trigger \
  -H "Content-Type: application/json" \
  -d '{"workflow":"new_project","description":"用户管理系统"}'
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Engine health + OpenCode connectivity |
| `POST` | `/webhook/lark` | 飞书事件订阅（默认渠道，单应用） |
| `POST` | `/webhook/lark/{app_name}` | 飞书事件订阅（多机器人） |
| `POST` | `/webhook/teams` | Teams messages from Power Automate |
| `POST` | `/webhook/approval` | 审批回调（Teams/Power Automate） |
| `POST` | `/pipeline/trigger` | Programmatic pipeline trigger |
| `GET` | `/pipeline/{run_id}/status` | Pipeline status |
| `GET` | `/observability/runs` | Recent pipeline runs |
| `GET` | `/observability/run/{run_id}` | Detailed run metrics |
| `GET` | `/observability/dashboard/{run_id}` | Mermaid dashboard (Markdown) |
| `POST` | `/yunxiao/webhook` | Yunxiao pipeline status callback |

飞书 CI/CD 审批通过卡片按钮完成（card.action.trigger 事件），
经 `/webhook/lark`（webhook 模式）或长连接（websocket 模式）回流。

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Engine Server | FastAPI + Python 3.11+ |
| AI Execution | OpenCode Server (HTTP API) + `@opencode-ai/sdk` |
| Agents | OpenCode subagents (YAML frontmatter .md files) |
| Skills | OpenCode skills (SKILL.md + templates/references/scripts) |
| State | File-based JSON (`.harness/states/`) |
| Observability | JSONL logs + Mermaid dashboards |
| DevOps | Yunxiao 云效 (Codeup → Flow → AppStack → ACK) |
| Communication | 飞书（默认）/ Teams / Power Automate，`NOTIFY_CHANNEL` 可配置 |

## Installation

```bash
# Install agents/skills/commands to OpenCode
./install.sh

# Install only for OpenCode
./install.sh --opencode

# Update after git pull
./install.sh --update
```
