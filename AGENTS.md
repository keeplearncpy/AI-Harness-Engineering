# AI Harness Engineering — AGENTS.md

## Project Identity
This repository is **AI Harness Engineering** — a dual-purpose toolkit for AI-powered full-stack project scaffolding.

### Mode 1: Local Toolkit
When installed via `install.sh`, each `agents/*.md` and `skills/*/` becomes an OpenCode subagent/skill that can be used in any project.

### Mode 2: Agent Loop Engine
This repo itself runs as an orchestrator agent loop. The `harness-orchestrator` agent coordinates subagents, listens for Teams webhooks, and integrates with Yunxiao (云效) for CI/CD.

## Key Conventions
- All agents use YAML frontmatter with `name`, `description`, `mode`, `model`, `temperature`, `permission` fields
- Skills are directories with `SKILL.md` as entry point, `templates/` for output patterns, `references/` for standards
- Commands are markdown files in `commands/` with YAML frontmatter for `/harness-*` shortcuts
- Agents follow a pipeline: FSD → [Prototype | Data Model] → [Frontend | Backend] → Test → Review → Deploy
- Tech stack is decided in the FSD phase and written into SSD「技术选型」章节; dev agents resolve it dynamically (project_context > SSD > fallback default), never hardcoded
- FSD docs live under `fsd/{模块}/feature-{功能名}-{索引}.md`（bug 修复为 `fix-bug-{修复名}-{索引}.md`）
- Prototype outputs HTML wireframes under `prototype/` with `click-map.md`（页面/路由/菜单/按钮/表单点击关系，无图片）
- Observability runs as a sidecar — never blocks the pipeline
- All Chinese content uses 中文; code comments use English

## Directory Layout
```
skills/<skill-name>/SKILL.md      — Skill definition (loaded by agents)
skills/<skill-name>/templates/    — Output templates (Markdown, code)
skills/<skill-name>/references/   — Standards, checklists, guides
skills/<skill-name>/scripts/      — Executable scripts

agents/<agent-name>.md            — Agent definition (YAML frontmatter + instructions)
commands/harness-<action>.md      — Command shortcuts
```
