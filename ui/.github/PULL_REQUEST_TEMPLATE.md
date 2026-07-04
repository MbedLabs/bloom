## Summary

## Checklist (UI)

- [ ] `npm run lint` and `npx tsc --noEmit` pass
- [ ] Vitest added/updated for new UI behavior
- [ ] Role enum matches backend (`admin` | `maintainer` | `external`)
- [ ] Detail pages wrapped in error boundary where applicable
- [ ] Loading state (skeleton/spinner) for new lists

## Verification

```bash
npm run lint && npx tsc --noEmit && npm run test
```
