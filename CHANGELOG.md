# Changelog

## Unreleased

### Added

- User-first deployment and operations guidance for the published Bloom PLM by EmbedLabs container image.
- Bounded ReqIF import processing: exactly one `.reqif` member, 25 MiB request and uncompressed-member limits, a 20:1 compression-ratio limit, and at most 100 archive entries.
- ReqIF object, relation, and hierarchy-depth limits, plus a streamed request cap, processing timeout, per-user rate limit, and one active import per project.

### Changed

- Bud integration now uses revocable 90-day `test-results:write` credentials instead of full administrator tokens.
- Bud submits test-case execution outcomes by Bloom `tc_id`; it does not create or synchronize campaigns.

### Fixed

- Campaigns now count as controlled documents in dashboard totals and per-project document counts.
- Authentication and project-access boundaries are consistently enforced across API routes.

### Security

- ReqIF archives are validated while streaming and parsed in a time-limited worker process.
- Signed webhook deliveries have replay protection.
- Python and npm dependency vulnerability scans block CI on actionable findings.
- Upgraded react-router to 7.18.1, closing moderate advisories including an open redirect via `<Link>`/`useNavigate` (GHSA-wrjc-x8rr-h8h6).

## 1.0.0

- Initial beta release of Bloom PLM by EmbedLabs as a self-hosted product lifecycle management platform.
- Published a multi-architecture container image with PostgreSQL-backed deployment, migrations, health checks, and persistent project data.
