# Changelog

## Unreleased

### Security and reliability

- enforce authentication boundaries across API routes and signed webhook delivery replay protection
- stream and strictly validate bounded ReqIF archives before time-limited parsing
- replace long-lived administrator integration tokens with revocable 90-day `test-results:write` service credentials
- run blocking Python and npm dependency vulnerability checks in CI

### Integration

- clarify that Bud submits test-case outcomes by Bloom `tc_id` and never synchronizes campaigns

## 1.0.0

- Combined the Bloom backend and web interface into one product repository and image.
- Added PostgreSQL-backed deployment, migrations, health checks, and product CI.
