# FSD Writing Guide

> Quality checklist for FSD generation. Use during self-review before output.

## Structural Completeness
- [ ] All required chapters (1-9) are filled
- [ ] feature_id follows kebab-case naming convention
- [ ] Each User Story contains role / action / benefit elements
- [ ] Acceptance criteria ≥ 3 items, all testable

## Requirement Quality
- [ ] No ambiguous language ("etc", "probably", "roughly")
- [ ] Exception flows ≥ 2 scenarios
- [ ] Business rules explicitly listed, not implied in flow text
- [ ] Non-functional requirements have specific metrics

## Data Consistency
- [ ] Core data entities identified with explicit field types
- [ ] Entity relationships annotated (1:1 / 1:N / M:N)
- [ ] Data flow descriptions consistent with API endpoints

## Traceability
- [ ] Each feature traceable to at least one User Story
- [ ] Each acceptance criterion maps to specific feature point
- [ ] Open questions tagged with `[待确认]` and assigned owner/deadline

## Downstream Compatibility
- [ ] Data entity naming consistent with data_modeler conventions
- [ ] API paths follow RESTful conventions
- [ ] UI descriptions sufficient to support UI interaction document generation
