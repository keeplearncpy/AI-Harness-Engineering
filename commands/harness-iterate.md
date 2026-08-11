---
name: harness-iterate
description: Iterate on an existing project — add features, fix bugs, or refactor code
---

# /harness-iterate — Iterative Development

Add features, fix bugs, or refactor code in an existing project. The pipeline loads project context and applies changes incrementally.

## Usage
```
/harness-iterate <change_description>
```

## Pipeline

```
┌──────────────────────────────────────────────────────────────┐
│  Step 1: Context Loading                                     │
│  Load existing project state, FSDs, and source code          │
├──────────────────────────────────────────────────────────────┤
│  Step 2: Intent Parsing                                      │
│  Determine change type: feature_add | bug_fix | refactor     │
├──────────────────────────────────────────────────────────────┤
│  Step 3: Requirements Update (if new feature)                │
│  Agent: harness-fsd → Delta FSD                              │
├──────────────────────────────────────────────────────────────┤
│  Step 4: Code Changes (Parallel if both frontend+backend)    │
│  Agent: harness-frontend-dev + harness-backend-dev           │
│  Input:  Existing code + Delta requirements                  │
│  Output: Updated source files (in-place or delta)            │
├──────────────────────────────────────────────────────────────┤
│  Step 5: Testing                                             │
│  Agent: harness-tester → Updated tests + Report              │
├──────────────────────────────────────────────────────────────┤
│  Step 6: Quality Review                                      │
│  Agent: harness-reviewer → Review report                     │
├──────────────────────────────────────────────────────────────┤
│  Step 7: Documentation Update                                │
│  Update CHANGELOG.md + INDEX.md                              │
└──────────────────────────────────────────────────────────────┘
```

## Examples

```bash
# Add a new feature
/harness-iterate 添加密码重置功能，通过邮箱发送重置链接

# Fix a bug
/harness-iterate 修复用户列表分页后第二页不显示数据的问题

# Refactor
/harness-iterate 重构认证模块，改为JWT token方式
```

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| change_description | Yes | Description of the change to make |
| --type | No | Change type: feature, fix, refactor (auto-detected if omitted) |
| --scope | No | Scope: frontend, backend, fullstack (auto-detected if omitted) |
