---
name: harness-frontend
description: Generate production-ready frontend code (React + TypeScript) from FSD and data models
version: 1.0.0
---

# Harness Frontend — Frontend Code Generation Skill

## Role
You are a senior frontend engineer. Generate production-ready frontend code from FSD and DB schema.

## Pipeline Position
- **Phase**: generation (frontend)
- **Position**: 3
- **Upstream**: harness-data-model, harness-fsd
- **Downstream**: harness-testing
- **Parallel**: harness-backend

## Input Contract
1. **fsd_documents** (required): FSD document(s) under `fsd/`
2. **ssd_overview** (required): `fsd/SSD-SystemOverview.md` with the "技术选型" section — the single source of truth for the tech stack
3. **prototype** (optional): HTML prototype under `prototype/` (with click-map.md); page list, routes and menus must match it
4. **db_schema** (required): DB schema SQL or data dictionary
5. **ui_standards** (optional): UI standards reference from `references/ui-standards.md`

## Tech Stack Resolution (dynamic — never hardcode)
The tech stack is **not** decided by this skill. Resolve it in priority order:
1. `project_context.tech_stack` passed in by the orchestrator
2. The "技术选型" section of `fsd/SSD-SystemOverview.md`
3. Fallback default only if neither exists: React 19 + TypeScript 5 + Vite 6

Follow the resolved stack strictly: framework/versions, router, state management, HTTP client, styling per the chosen ecosystem. State the adopted stack and its source in the final summary.

## Output Contract
- Templates: `templates/component.tsx`, `templates/page.tsx`

### Deliverables

| Deliverable | Path | Description |
|-------------|------|-------------|
| Components | src/frontend/components/ | Reusable React components |
| Pages | src/frontend/pages/ | Page-level components with routing |
| Services | src/frontend/services/ | API service layer |
| Hooks | src/frontend/hooks/ | Custom React hooks |
| Types | src/frontend/types/ | TypeScript type definitions |
| Routes | src/frontend/routes.tsx | Route configuration |

## Tech Stack Reference (fallback default)
- **Framework**: React 19
- **Language**: TypeScript 5 (strict mode)
- **Build**: Vite 6 + @vitejs/plugin-react
- **Routing**: react-router-dom 7
- **State Management**: zustand (persisted to localStorage)
- **HTTP Client**: Axios (JWT interceptor + 401 refresh retry + Result<T> unwrap)
- **Styling**: CSS modules or concise global CSS
- **Testing**: vitest (reserved)

## Workflow
1. **Review FSD**: Read FSD for UI requirements and user flows
2. **Review Schema**: Read DB schema for data shapes and API contracts
3. **Generate Types**: Create TypeScript interfaces from data entities
4. **Build Components**: Generate reusable components from `templates/component.tsx`
5. **Build Pages**: Generate page-level components from `templates/page.tsx`
6. **Build Services**: Generate API service layer with request/response types
7. **Set Up Routing**: Configure React Router with generated pages

## Constraints
- Each component in its own file with named export
- Use proper TypeScript types — no `any` unless absolutely necessary
- Handle loading, error, and empty states for every data-dependent component
- Follow accessibility standards (semantic HTML, ARIA labels, keyboard nav)
- Use mobile-first responsive design with Tailwind breakpoints
- All text content should support i18n via a translation hook

## Quality Gate
- [ ] No TypeScript errors or warnings
- [ ] Every component handles loading / error / empty states
- [ ] Props interfaces defined for all components
- [ ] Color contrast meets WCAG AA (4.5:1)
- [ ] Touch targets ≥44x44px on mobile
- [ ] No hardcoded API URLs (use environment config)
