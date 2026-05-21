## Summary

<!-- What changed and why -->

## Checklist (backend)

- [ ] No new N+1 queries (batch `IN()` or `selectinload`)
- [ ] New FK columns have indexes / Alembic revision
- [ ] Pytest added or updated for changed routes
- [ ] `black --check` / `isort --check` / `pytest` pass locally
- [ ] Auth on new endpoints (`get_current_user` / `require_role`)

## Verification

```bash
black --check --diff app/ tests/
isort --profile black --check-only --diff app/ tests/
pytest tests/ -v
```
