---
name: harness-iterate
description: Iterate on an existing project — runs the local delta workflow (FSD delta → Prototype update → Code changes → Test → Review)
---

# /harness-iterate — 本地增量开发工作流

> 本命令是**本地 opencode 增量工作流入口**。执行本命令时，你（主 agent）扮演编排器，
> 按变更类型（新功能 / bug 修复 / 重构）执行增量流水线。每个阶段等待子代理返回后再继续。

## 子代理名映射

同 `/harness-new`：优先探测 `harness-*`（全局安装），回退到项目内 `.opencode/agents` 名
（`fsd_generator`、`prototype_generator`、`data_modeler`、`backend_dev`、`frontend_dev`、`tester`、`code-reviewer`）。
可观测性用全局名 `harness-observability`。

## 增量流水线

### Step 1: 上下文加载
- 读取 `fsd/SSD-SystemOverview.md`（技术选型）、`fsd/INDEX.md`、现有前后端代码结构
- 判断变更类型：feature_add | bug_fix | refactor

### Step 2: 需求增量（新功能 / bug 修复时）
- 调用 fsd 子代理产出增量文档：
  - 新功能：`fsd/{模块}/feature-{功能名称}-{索引}.md`（索引 = 模块内 max+1）
  - Bug 修复：`fsd/{模块}/fix-bug-{修复名称}-{索引}.md`（含缺陷描述/复现/根因/修复方案/验收标准）
  - 同步更新 `fsd/INDEX.md`

### Step 3: 原型增量（页面结构有变化时）
- 调用原型子代理更新 `prototype/` 与 `click-map.md`

### Step 4: 代码修改（前后端都涉及则并行）
- 后端子代理：附增量 FSD + 现有 `backend/` 路径 + 技术选型，原地修改
- 前端子代理：附增量 FSD + `prototype/` + 现有 `frontend/` 路径 + 技术选型，原地修改

### Step 5: 测试增量
- 测试子代理：更新 `tests/` 用例并回归

### Step 6: 评审
- 评审子代理：评审改动；严重问题要求修复

### Step 7: 可观测性报告（每次会话必做，生成一次）
- 调用可观测性子代理，附项目根目录绝对路径 + 本次会话 run_id（时间戳 `YYYYMMDD-HHMMSS`）
- 产出 `docs/observability/` 下 summary/dashboard/execution 报告并更新 INDEX.md
- 即使前面步骤失败也必须执行本步骤

## 硬性规则
1. 不重复生成已有产物，只做增量；重构可修改现有文件
2. 技术栈沿用 `fsd/SSD-SystemOverview.md`，不擅自更换
3. 每个子代理任务必须给出绝对路径输入与输出
4. 子代理返回空时重试一次；仍失败则停下向用户报告
5. 会话结束必须执行 Step 7 产出可观测性报告（每次会话一份）
6. 完成后输出变更总览：改动的文档/代码文件清单、测试与评审结论、可观测性报告链接

## 参数

| Parameter | Required | Description |
|-----------|----------|-------------|
| change_description | Yes | Description of the change to make |
| --type | No | Change type: feature, fix, refactor (auto-detected if omitted) |
| --scope | No | Scope: frontend, backend, fullstack (auto-detected if omitted) |
