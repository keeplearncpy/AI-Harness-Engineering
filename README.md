# AI Harness Engineering

AI-powered full-stack project scaffolding and iteration platform.

## Structure

- `config/` — Global configuration, prompts, and workflow definitions
- `agents/` — Agent definitions (subagents + independent agents)
- `skills/` — Templates, schemas, and checklists
- `workspace/` — Per-project output (docs, design, src, tests)
- `core/` — Core engine: orchestrator, context manager, agent loader, validator

## Getting Started

```bash
pip install -r requirements.txt
python core/main.py
```
