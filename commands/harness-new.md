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
│  Output: FSD documents + SSD overview                        │
├──────────────────────────────────────────────────────────────┤
│  Phase 2: Data Modeling                                      │
│  Agent: harness-data-modeler                                 │
│  Input:  FSD documents                                       │
│  Output: DB schema (DDL) + ER diagram + Data dictionary      │
├──────────────────────────────────────────────────────────────┤
│  Phase 3: Code Generation (Parallel)                         │
│  Agent: harness-frontend-dev + harness-backend-dev           │
│  Input:  FSD + DB schema                                     │
│  Output: Frontend (React/TS) + Backend (FastAPI/Python)      │
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
| --tech-frontend | No | Frontend framework (default: react) |
| --tech-backend | No | Backend framework (default: fastapi) |
| --tech-database | No | Database (default: postgresql) |
| --output | No | Output directory (default: ./workspace/{project_name}) |
