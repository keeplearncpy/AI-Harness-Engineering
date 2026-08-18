---
name: harness-new
description: Create a new full-stack project — runs the full local workflow (FSD → Prototype/Data Model → Frontend/Backend → Test → Review)
---

# /harness-new — 本地全流程脚手架工作流

> 本命令是**本地 opencode 工作流入口**。执行本命令时，你（主 agent）扮演编排器，
> 按下方阶段依次调用子代理完成整个流水线。每个阶段都必须等待子代理返回结果后再继续，
> 并把上游产物路径写入下一个子代理的任务描述中。

## 子代理名映射

按以下顺序探测可用的子代理名，使用第一个存在的：

| 角色 | 全局安装名（install.sh） | 项目内名（.opencode/agents） |
|------|--------------------------|------------------------------|
| 需求分析 | `harness-fsd` | `fsd_generator` |
| 原型设计 | `harness-prototype` | `prototype_generator` |
| 数据建模 | `harness-data-modeler` | `data_modeler` |
| 后端开发 | `harness-backend-dev` | `backend_dev` |
| 前端开发 | `harness-frontend-dev` | `frontend_dev` |
| 测试 | `harness-tester` | `tester` |
| 代码评审 | `harness-reviewer` | `code-reviewer` |

## 流水线阶段（当前项目根目录下执行）

### Phase 1: FSD（需求分析）
- 用 Task 工具调用 fsd 子代理，任务描述包含：用户原始需求 + 输出要求
  （SSD 写到 `fsd/SSD-SystemOverview.md` 且必须含「技术选型」章节；
  feature 文档写到 `fsd/{模块}/feature-{功能名}-{索引}.md`；更新 `fsd/INDEX.md`）

### Phase 2: 原型 + 数据建模（并行，一次消息里两个 Task）
- 原型子代理：输出 `prototype/`（HTML 线框 + click-map.md，禁止图片）
- 数据建模子代理：输出 `design/db-schema.sql` + ER 图 + 数据字典，
  任务描述中附上 Phase 1 产出的技术选型（数据库方言必须一致）

### Phase 3: 代码生成（并行，一次消息里两个 Task）
- 后端子代理：输出 `backend/`，任务描述附 FSD 路径 + schema 路径 + 技术选型（SSD 为准）
- 前端子代理：输出 `frontend/`，任务描述附 FSD 路径 + 原型路径 + schema 路径 + 技术选型

### Phase 4: 测试
- 测试子代理：输入 FSD + 前后端代码路径，输出 `tests/` 用例与报告

### Phase 5: 评审
- 评审子代理：输入全部生成代码，输出评审报告；有严重问题则要求修复后复评

## 硬性规则
1. 阶段顺序不可跳；并行阶段用同一条消息发起两个 Task
2. 每个子代理任务必须给出**绝对路径**输入（FSD/schema/原型）与输出目录
3. 技术栈唯一来源是 `fsd/SSD-SystemOverview.md` 的「技术选型」章节，不要自行改栈
4. 子代理返回空/失败时，重试一次并带上更明确的路径；仍失败则停下来向用户报告
5. 全部完成后输出总览：目录树、各阶段产物路径、接口/页面数量

## 参数

| Parameter | Required | Description |
|-----------|----------|-------------|
| project_description | Yes | Natural language description of the product |
| --tech-frontend | No | 指定前端栈（默认由 FSD 阶段决定：React 19 + Vite） |
| --tech-backend | No | 指定后端栈（默认由 FSD 阶段决定：Java 21 + Spring Boot 3.x） |
| --tech-database | No | 指定数据库（默认由 FSD 阶段决定：MySQL 8） |
| --output | No | 输出目录（默认当前工作目录） |
