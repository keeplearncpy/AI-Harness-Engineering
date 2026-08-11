# Teams Webhook Integration Guide

> Setup guide for Microsoft Teams incoming/outgoing webhooks with AI Harness.

## Prerequisites

1. Microsoft Teams team with admin permissions
2. Power Automate license (for approval workflows)
3. Incoming webhook URL for the target channel

## Setup Incoming Webhook

1. In Teams, go to the channel → `...` → Connectors
2. Search for "Incoming Webhook" → Configure
3. Name it "AI Harness Engineering"
4. Copy the webhook URL → set as `TEAMS_WEBHOOK_URL` env var

## Setup Power Automate Flow

1. Open [Power Automate](https://make.powerautomate.com)
2. Create a new flow: "When a Teams message is received"
3. Add trigger condition: message starts with `/harness-`
4. Action: HTTP request to Harness webhook endpoint
5. Add approval step: "Start and wait for an approval"
6. Action: Send approval result back to Harness

## Environment Variables

```bash
# Required
export TEAMS_WEBHOOK_URL="https://prod-xxx.webhook.office.com/webhookb2/..."
export TEAMS_APP_ID="your-teams-app-id"

# Optional
export POWER_AUTOMATE_ENV="default-xxx"
export POWER_AUTOMATE_FLOW_ID="xxx"
```

## Message Format

### Outgoing (Harness → Teams)

Harness sends messages as Adaptive Cards via the incoming webhook URL:

```bash
curl -X POST "$TEAMS_WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{"type":"message","attachments":[...]}'
```

### Incoming (Teams → Harness)

Teams messages are parsed by Power Automate and forwarded to the Harness webhook listener:

- Commands prefixed with `/harness-new` → new project
- Commands prefixed with `/harness-iterate` → iteration
- Replies to Adaptive Card actions → approval/status actions

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Webhook returns 400 | Check JSON payload format, Adaptive Card schema |
| Messages not received | Verify webhook URL is active (not expired) |
| Power Automate flow not triggered | Check trigger conditions and flow status |
| Approval times out | Increase flow timeout or check approver availability |
| Duplicate messages | Harness detects duplicates via `run_id` in payload |

## Security Notes

- Webhook URLs are secrets — treat them like passwords
- Rotate webhook URLs periodically
- Restrict Power Automate flow access to authorized users
- Use HTTPS for all webhook communications
- Validate incoming message signatures where possible
