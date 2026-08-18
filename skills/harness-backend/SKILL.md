---
name: harness-backend
description: Generate production-ready backend code (Java 21 + Spring Boot 3.x + MySQL 8) from FSD and DB schema
version: 2.0.0
---

# Harness Backend — Backend Code Generation Skill

## Role
You are a senior backend engineer. Generate production-ready Java 21 + Spring Boot 3.x backend code from FSD and DB schema.

## Pipeline Position
- **Phase**: generation (backend)
- **Position**: 3
- **Upstream**: harness-data-model, harness-fsd, harness-prototype
- **Downstream**: harness-testing
- **Parallel**: harness-frontend

## Input Contract
1. **fsd_documents** (required): FSD document(s) under `fsd/`
2. **ssd_overview** (required): `fsd/SSD-SystemOverview.md` with the "技术选型" section — the single source of truth for the tech stack
3. **db_schema** (required): DB schema SQL under `design/db-schema.sql`
4. **api_standards** (optional): API design standards from `references/api-standards.md`

## Tech Stack Resolution (dynamic — never hardcode)
The tech stack is **not** decided by this skill. Resolve it in priority order:
1. `project_context.tech_stack` passed in by the orchestrator
2. The "技术选型" section of `fsd/SSD-SystemOverview.md`
3. Fallback default only if neither exists: Java 21 + Spring Boot 3.3.x + Maven + MySQL 8

Follow the resolved stack strictly: language/framework/versions, ORM, DB dialect, auth scheme, ecosystem libraries. State the adopted stack and its source in the final summary.

## Output Contract
- Templates: `templates/controller.ts`, `templates/service.ts`, `templates/router.ts` (reference patterns; final code is Java)

### Deliverables

| Deliverable | Path | Description |
|-------------|------|-------------|
| Maven config | backend/pom.xml | Spring Boot 3.3.x + Java 21 dependencies |
| Config | backend/src/main/java/{pkg}/config/ | SecurityConfig, CorsConfig, RedisConfig, OpenApiConfig |
| Auth | backend/src/main/java/{pkg}/auth/ | Login/register/refresh/logout, JwtUtil, session management |
| Modules | backend/src/main/java/{pkg}/{module}/ | Controller/Service/Repository per FSD module |
| Common | backend/src/main/java/{pkg}/common/ | Result<T>, global exception handler, pagination |
| App config | backend/src/main/resources/application.yml | Datasource, Redis, JWT, port |
| SQL | backend/src/main/resources/db/schema.sql | Copy of design/db-schema.sql |

## Tech Stack Reference (fallback default)
- **Language**: Java 21
- **Framework**: Spring Boot 3.3.x
- **Build**: Maven
- **ORM**: Spring Data JPA or MyBatis (pick one, stay consistent)
- **Database**: MySQL 8
- **Auth**: jjwt 0.12.x + Spring Security (optional) + BCrypt
- **Cache**: spring-boot-starter-data-redis
- **Docs**: springdoc-openapi 2.x
- **Utils**: Lombok, spring-boot-starter-validation, mysql-connector-j

## Workflow
1. **Review FSD**: Read FSD for API requirements and business logic
2. **Review Schema**: Read DB schema, generate entities/repositories
3. **Scaffold**: pom.xml, application.yml, main class
4. **Common layer**: Result<T>, exception handling, pagination
5. **Auth**: JwtUtil (sign/verify/blacklist), auth endpoints
6. **Modules**: Controller → Service → Repository per FSD module
7. **SQL**: Copy design/db-schema.sql into resources/db/
8. **README**: startup instructions

## Constraints
- RESTful API design with proper HTTP status codes
- Unified response envelope `Result<T> {code, message, data}`
- Input validation on all endpoints (jakarta validation)
- BCrypt for passwords; JWT access token (short) + refresh token (long)
- Idempotency for write operations (request_id), transaction boundaries
- Pagination via unified Page wrapper
- Environment-based configuration (no hardcoded secrets)
- Code comments in English; API error messages may be Chinese

## Quality Gate
- [ ] Every FSD module has Controller/Service coverage
- [ ] Every endpoint has request/response DTO + validation
- [ ] Global exception handler covers validation and business errors
- [ ] schema.sql consistent with design/db-schema.sql
- [ ] Structured summary returned (file tree, endpoint count, key notes)
