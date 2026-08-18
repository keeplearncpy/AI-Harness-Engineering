---
name: harness-new
description: Create a new full-stack project from a product idea or requirements description
---

# /harness-new — New Project Scaffolding

Start a new project from scratch. Provide a product idea or requirements description, and the pipeline will generate a complete full-stack application.

## Usage
```
/harness-new <project_description>
```

## Pipeline

```
┌──────────────────────────────────────────────────────────────┐
│  Phase 1: Requirements Analysis                              │
│  Agent: harness-fsd                                          │
│  Input:  User's product description                          │
│  Output: fsd/SSD-SystemOverview.md (含技术选型章节)          │
│          + fsd/{模块}/feature-*.md                           │
├──────────────────────────────────────────────────────────────┤
│  Phase 2: Prototype + Data Modeling (Parallel)               │
│  Agent: harness-prototype | harness-data-modeler             │
│  Input:  FSD documents + tech stack (from SSD)               │
│  Output: prototype/ HTML 线框 + click-map.md                 │
│          design/db-schema.sql + ER diagram + Data dictionary │
├──────────────────────────────────────────────────────────────┤
│  Phase 3: Code Generation (Parallel)                         │
│  Agent: harness-frontend-dev + harness-backend-dev           │
│  Input:  FSD + prototype + DB schema + tech stack (from SSD) │
│  Output: Frontend + Backend（技术栈以 SSD 技术选型为准）     │
├──────────────────────────────────────────────────────────────┤
│  Phase 4: Testing                                            │
│  Agent: harness-tester                                       │
│  Input:  Generated code + FSD                                │
│  Output: Test cases + Test report                            │
├──────────────────────────────────────────────────────────────┤
│  Phase 5: Quality Review                                     │
│  Agent: harness-reviewer                                     │
│  Input:  All generated code + Test results                   │
│  Output: Review report with findings                         │
└──────────────────────────────────────────────────────────────┘
```

## Example
```
/harness-new 一个用户管理系统，支持注册、登录、角色管理和权限分配
```

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| project_description | Yes | Natural language description of the product |
| --tech-frontend | No | Frontend framework (default: react 19 + vite) |
| --tech-backend | No | Backend framework (default: java 21 + spring boot 3.x) |
| --tech-database | No | Database (default: mysql 8) |
| --with-prototype | No | Generate HTML prototype (default: true) |
| --output | No | Output directory (default: ./workspace/{project_name}) |
