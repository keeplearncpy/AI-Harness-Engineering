# Zentao Integration Checklist

> Quality checklist for Zentao PMS integration.

## Authentication
- [ ] Zentao API URL correctly configured
- [ ] API credentials stored in environment variables (not hardcoded)
- [ ] Session token management with refresh logic
- [ ] Connection timeout and retry configured

## Story Management
- [ ] User story fields mapped correctly (title, description, priority, assignee)
- [ ] Story status transitions follow Zentao workflow
- [ ] FSD-to-story mapping preserved for traceability

## Task Management
- [ ] Task estimated hours calculated from module complexity
- [ ] Task dependencies reflect code module dependencies
- [ ] Task assignment follows team capacity rules

## Bug Tracking
- [ ] Bug severity mapped from test case priority (P0 → 1, P1 → 2, P2 → 3)
- [ ] Bug steps-to-reproduce auto-generated from test case
- [ ] Bug includes code file:line reference

## Error Handling
- [ ] API failures logged with full context
- [ ] Failed operations queued for retry
- [ ] User notified of integration failures
- [ ] No data loss on partial failures
