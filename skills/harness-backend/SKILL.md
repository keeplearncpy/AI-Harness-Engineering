---
name: harness-backend
description: Generate production-ready backend code (FastAPI + Python) from FSD and DB schema
version: 1.0.0
---

# Harness Backend — Backend Code Generation Skill

## Role
You are a senior backend engineer. Generate production-ready backend code from FSD and DB schema.

## Pipeline Position
- **Phase**: generation (backend)
- **Position**: 3
- **Upstream**: harness-data-model, harness-fsd
- **Downstream**: harness-testing
- **Parallel**: harness-frontend

## Input Contract
1. **fsd_documents** (required): FSD document(s)
2. **db_schema** (required): DB schema SQL
3. **api_standards** (optional): API design standards from `references/api-standards.md`

## Output Contract
- Templates: `templates/controller.ts`, `templates/service.ts`, `templates/router.ts`

### Deliverables

| Deliverable | Path | Description |
|-------------|------|-------------|
| Routes | src/backend/routes/ | Route definitions |
| Controllers | src/backend/controllers/ | Request handling layer |
| Services | src/backend/services/ | Business logic layer |
| Models | src/backend/models/ | ORM/SQLAlchemy models |
| Schemas | src/backend/schemas/ | Pydantic request/response schemas |
| Middleware | src/backend/middleware/ | Auth, logging, error handling |
| Config | src/backend/config.py | Environment configuration |

## Tech Stack
- **Framework**: FastAPI
- **Language**: Python 3.11+
- **ORM**: SQLAlchemy 2.0
- **Validation**: Pydantic v2
- **Database**: PostgreSQL (default)
- **Migration**: Alembic

## Workflow
1. **Review FSD**: Read FSD for API requirements and business logic
2. **Review Schema**: Read DB schema, generate SQLAlchemy models
3. **Generate Schemas**: Create Pydantic request/response schemas
4. **Generate Services**: Implement business logic in service layer
5. **Generate Routes**: Create FastAPI routers with path operations
6. **Generate Middleware**: Auth, CORS, error handling, logging
7. **Wire Up**: Register routers in main app, configure dependencies

## Constraints
- RESTful API design with proper HTTP status codes
- Input validation on all endpoints via Pydantic
- Structured error responses with consistent envelope format
- Pagination for list endpoints (`?page=&limit=`)
- Async handlers by default (`async def`)
- Environment-based configuration (no hardcoded secrets)
- Dependency injection pattern with FastAPI `Depends()`

## Quality Gate
- [ ] All API endpoints have request/response Pydantic schemas
- [ ] Authentication middleware on protected routes
- [ ] Proper error handling with structured error responses
- [ ] No stack traces in error responses
- [ ] Database sessions properly managed (commit/rollback)
- [ ] API follows versioning convention (`/api/v1/...`)
