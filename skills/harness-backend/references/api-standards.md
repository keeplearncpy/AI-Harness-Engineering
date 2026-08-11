# API Design Standards

> Backend API design standards and checklist.

## Endpoint Design
- [ ] RESTful naming conventions (nouns, not verbs)
- [ ] Proper HTTP methods (GET, POST, PUT, PATCH, DELETE)
- [ ] Versioned API paths (`/api/v1/...`)
- [ ] Consistent response envelope format

## Request Handling
- [ ] Input validation on all endpoints (Pydantic / Joi / Zod)
- [ ] Proper HTTP status codes (200, 201, 400, 401, 403, 404, 500)
- [ ] Pagination for list endpoints (`?page=&limit=`)
- [ ] Sorting and filtering support

## Response Format
```json
{
  "success": true,
  "data": {},
  "error": null,
  "meta": {
    "page": 1,
    "limit": 20,
    "total": 100
  }
}
```

## Security
- [ ] Authentication required for protected routes
- [ ] Authorization checks (role-based access)
- [ ] Rate limiting on public endpoints
- [ ] CORS configured correctly
- [ ] Input sanitization against XSS/SQL injection

## Error Handling
- [ ] Structured error responses
- [ ] No stack traces in production responses
- [ ] Logging for all server errors
- [ ] Graceful degradation on dependency failures

## Documentation
- [ ] OpenAPI/Swagger docs generated
- [ ] Each endpoint has a description
- [ ] Request/response examples provided
