---
name: harness-teams
description: Microsoft Teams + Power Automate integration — receive tasks, send notifications, trigger approvals in the development pipeline
version: 1.0.0
---

# Harness Teams — Microsoft Teams & Power Automate Integration

## Role
You bridge AI Harness Engineering with Microsoft Teams and Power Automate. You receive development tasks from Teams, send pipeline status notifications, trigger approval workflows via Power Automate, and enable the full project lifecycle within the Teams ecosystem.

## Core Capabilities

### 1. Teams Incoming Webhook
- Receive task creation requests from Teams channels
- Parse structured commands from Teams messages (`/harness-new`, `/harness-iterate`)
- Extract project requirements from Teams Adaptive Cards

### 2. Teams Outgoing Notifications
- Send pipeline phase status updates to Teams channels
- Post code review results as threaded messages
- Notify on pipeline completion, errors, or needed approvals

### 3. Power Automate Integration
- Trigger Power Automate flows for approval workflows (code review sign-off, deployment approval)
- Receive Power Automate flow results and feed back to orchestrator
- Map pipeline phases to Power Automate business process flows

### 4. Adaptive Card Design
- Generate interactive Adaptive Cards for task creation, status updates, and approvals
- Support actionable buttons: Approve, Reject, Re-run, Deploy
- Display pipeline dashboards inline via card rendering

## Input Contract

### Teams → Harness (Incoming)

| Event | Payload | Action |
|-------|---------|--------|
| New project request | `{ type: "new_project", description, channel_id, user }` | Trigger `/harness-new` |
| Feature request | `{ type: "iterate", description, channel_id, user }` | Trigger `/harness-iterate` |
| Approval response | `{ type: "approval", approved: bool, comments, flow_id }` | Resume pipeline or abort |
| Status query | `{ type: "status", run_id }` | Return current pipeline status |

### Harness → Teams (Outgoing)

| Event | Adaptive Card | Channel |
|-------|--------------|---------|
| Pipeline started | Pipeline status card with progress indicator | Project channel |
| Phase completed | Phase summary card with output preview | Project channel |
| Code review ready | Approval card with Approve/Reject buttons | Review channel |
| Pipeline completed | Final summary card with artifact links | Project channel |
| Error occurred | Error alert card with retry button | Project channel + Admin |

## Workflow

```
Teams Channel                    AI Harness                    Power Automate
    │                                │                              │
    │── /harness-new "用户系统" ───→│                              │
    │                                │── Start Pipeline             │
    │←── Pipeline started card ─────│                              │
    │                                │── FSD done                   │
    │←── Phase 1 complete card ─────│                              │
    │                                │── DB Schema done             │
    │←── Phase 2 complete card ─────│                              │
    │                                │── Code generated             │
    │                                │── Code review needed         │
    │                                │──────────────────────────→│ Start approval flow
    │←── Approval card ─────────────│←──────────────────────────│
    │── Approve ─────────────────→│──────────────────────────→│ End approval flow
    │                                │←──────────────────────────│ Approved
    │                                │── Testing                   │
    │←── Pipeline complete card ────│                              │
    │                                │                              │
```

## Adaptive Card Templates

### Pipeline Status Card
```json
{
  "type": "AdaptiveCard",
  "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
  "version": "1.5",
  "body": [
    { "type": "TextBlock", "text": "🚀 Pipeline: {{project_name}}", "weight": "Bolder", "size": "Large" },
    { "type": "FactSet", "facts": [
      { "title": "Run ID", "value": "{{run_id}}" },
      { "title": "Phase", "value": "{{current_phase}}/5" },
      { "title": "Status", "value": "{{status}}" }
    ]},
    { "type": "TextBlock", "text": "{{phase_description}}", "wrap": true }
  ]
}
```

### Approval Card
```json
{
  "type": "AdaptiveCard",
  "body": [
    { "type": "TextBlock", "text": "📋 Code Review Ready", "weight": "Bolder" },
    { "type": "TextBlock", "text": "{{review_summary}}", "wrap": true },
    { "type": "FactSet", "facts": [
      { "title": "Critical issues", "value": "{{critical_count}}" },
      { "title": "High issues", "value": "{{high_count}}" }
    ]}
  ],
  "actions": [
    { "type": "Action.Submit", "title": "✅ Approve", "data": { "action": "approve" } },
    { "type": "Action.Submit", "title": "❌ Reject", "data": { "action": "reject" } },
    { "type": "Action.ShowCard", "title": "💬 Comment", "card": { "body": [{ "type": "Input.Text", "id": "comments" }], "actions": [{ "type": "Action.Submit", "title": "Submit" }] } }
  ]
}
```

## Constraints
- All Teams webhook URLs stored in environment variables, never in code
- Rate limit Teams message sending (max 5 messages/second)
- Idempotent handling of duplicate incoming requests
- Adaptive Cards version 1.5 for maximum compatibility
- Fallback to plain text messages if Adaptive Card rendering fails
- All Power Automate flows include timeout (default: 24h for approvals)

## References
- `references/teams-integration.md` — Teams webhook setup & troubleshooting
