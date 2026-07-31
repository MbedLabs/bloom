# Changelog

## Unreleased

### Added

- Jira is supported alongside GitHub and GitLab, with the same security contract: a configured webhook secret makes HMAC verification mandatory, each delivery identifier is accepted only once, and credentials are encrypted at rest. Jira issues are matched by status category rather than by project-specific status names, and outbound status changes are applied as workflow transitions.
- Change requests can now track an external issue in any supported tracker, mirroring defects, and record their sync attempts in `change_request_sync_events`.
- `integration_settings.account_email` stores the Jira Cloud account that owns the API token.

### Changed

- Outbound status mapping is shared by defects and change requests, so change-request statuses (`Implemented`, `Approved`, `Under Review`, …) now open or close the linked issue correctly on GitHub and GitLab as well.

## 1.0.0 - 2026-07-24

Initial public beta release of Bloom PLM by EmbedLabs — a self-hosted product
lifecycle management platform. Published as a multi-architecture container image
with PostgreSQL-backed deployment, Alembic migrations, liveness/readiness health
checks, and persistent project data.

### Added

- User-first deployment and operations guidance for the published Bloom PLM by EmbedLabs container image.
- Bounded ReqIF import processing: exactly one `.reqif` member, 25 MiB request and uncompressed-member limits, a 20:1 compression-ratio limit, and at most 100 archive entries.
- ReqIF object, relation, and hierarchy-depth limits, plus a streamed request cap, processing timeout, per-user rate limit, and one active import per project.

### Changed

- Bud integration now uses revocable 90-day `test-results:write` credentials instead of full administrator tokens.
- Bud submits test-case execution outcomes by Bloom `tc_id`; it does not create or synchronize campaigns.
- Email changes are administrator-controlled: users may request a change, administrators approve or reject it, and the new mailbox must confirm before the login changes. Administrators can initiate the same confirmed workflow.

### Fixed

- Campaigns now count as controlled documents in dashboard totals and per-project document counts.
- Authentication and project-access boundaries are consistently enforced across API routes.

### Security

- External tracker credentials and webhook secrets are encrypted at rest (Fernet) and are never returned through APIs. Bloom remains fully usable without the optional key; only GitHub/GitLab tracker-secret operations fail closed.
- ReqIF archives are validated while streaming and parsed in a time-limited worker process.
- Signed webhook deliveries have replay protection.
- Passwords must be at least 12 characters; changing or resetting a password signs out all existing sessions.
- One-time links (invitation, email verification, password reset, email change) carry their token only in the URL fragment and are single-use, keeping tokens out of request targets, server logs, and the Referer header.
- Direct email replacement through the generic administrator user-update API is no longer allowed.
- Python and npm dependency vulnerability scans block CI on actionable findings.
- Upgraded React Router to 7.18.2 and the lint/test toolchain to patched releases. The remaining npm advisory affects only RSC Actions, which Bloom does not use, and is narrowly documented in the audit gate.

### Upgrade notes

- Migration `d20260722a06` clears legacy plaintext GitHub/GitLab tokens and webhook secrets and disables every affected tracker integration. Configure `INTEGRATION_ENCRYPTION_KEY`, re-enter rotated credentials, and explicitly enable each integration again.
- SMTP remains optional for a single-administrator evaluation, but invitations, password resets, and approved email changes require it.
