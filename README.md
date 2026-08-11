# AI Harness Engineering

AI-powered full-stack project scaffolding and iteration platform.

## Structure

```
ai-harness-engineering/
├── README.md
├── install.sh
│
├── skills/                              # Skill Layer (knowledge packs)
│   ├── harness-fsd/                     # Requirements → FSD
│   ├── harness-data-model/              # FSD → DB Schema
│   ├── harness-frontend/                # FSD + Schema → React/TypeScript
│   ├── harness-backend/                 # FSD + Schema → FastAPI/Python
│   ├── harness-testing/                 # Code + FSD → Tests
│   ├── harness-code-review/             # Code → Review Report
│   └── harness-zentao-agent/            # Zentao PMS Integration
│
├── agents/                              # Agent Layer (role definitions)
│   ├── harness-orchestrator.md          # Main orchestrator
│   ├── harness-fsd.md                   # Requirements analyst
│   ├── harness-data-modeler.md          # Database architect
│   ├── harness-frontend-dev.md          # Frontend developer
│   ├── harness-backend-dev.md           # Backend developer
│   ├── harness-tester.md                # QA engineer
│   ├── harness-reviewer.md              # Code reviewer
│   ├── harness-zentao-agent.md          # Zentao PMS agent
│   └── harness-yunxiao-agent.md         # Yunxiao cloud agent
│
└── commands/                            # Command shortcuts
    ├── harness-new.md                   # /harness-new — New project
    └── harness-iterate.md               # /harness-iterate — Iterate
```

## Pipeline

```
User Input → FSD → DB Schema → [Frontend + Backend] → Tests → Review → Deploy
```

## Getting Started

```bash
# Install agents & skills into your CLI tool
./install.sh

# Or update existing installation
./install.sh --update
```

## Commands

| Command | Description |
|---------|-------------|
| `/harness-new` | Create a new full-stack project from idea |
| `/harness-iterate` | Add features, fix bugs, or refactor |

## Tech Stack (Defaults)

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + TypeScript + Tailwind CSS |
| Backend | FastAPI + Python 3.11+ |
| Database | PostgreSQL + SQLAlchemy |
| Testing | Vitest + pytest + Playwright |
