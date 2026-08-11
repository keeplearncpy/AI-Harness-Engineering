# Code Review Checklist

> Comprehensive checklist for code review. Verify each item before approving code.

## Correctness
- [ ] Code implements the specified requirements from FSD
- [ ] Business logic matches acceptance criteria
- [ ] Edge cases and error conditions handled
- [ ] No off-by-one or boundary errors

## Security (OWASP Top 10)
- [ ] No hardcoded secrets, API keys, or credentials
- [ ] Input validation and sanitization on all user input
- [ ] SQL injection prevention (parameterized queries)
- [ ] XSS prevention (output encoding)
- [ ] CSRF protection on state-changing requests
- [ ] Proper authentication and authorization checks
- [ ] No sensitive data in logs or error messages
- [ ] HTTPS enforced for production

## Performance
- [ ] No N+1 query problems
- [ ] Database queries have appropriate indexes
- [ ] No unnecessary re-renders (frontend)
- [ ] Large lists use pagination or virtual scrolling
- [ ] Expensive computations memoized or cached

## Maintainability
- [ ] Clear and consistent naming conventions
- [ ] Functions are small and single-purpose (<50 lines)
- [ ] No duplicated code (DRY principle)
- [ ] Complex logic has explanatory comments
- [ ] Magic numbers replaced with named constants
- [ ] File structure follows project conventions

## Error Handling
- [ ] All async operations have error handling
- [ ] User-friendly error messages (no raw stack traces)
- [ ] Error states rendered in UI (not blank screens)
- [ ] Fallback behavior for degraded dependencies

## Testing
- [ ] Unit tests cover critical business logic
- [ ] Integration tests cover API contracts
- [ ] Test coverage meets project threshold
- [ ] Tests are isolated and idempotent
