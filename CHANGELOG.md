# Changelog

## Unreleased

### Added

- Jira is supported alongside GitHub and GitLab, with the same security contract: a configured webhook secret makes HMAC verification mandatory, each delivery identifier is accepted only once, and credentials are encrypted at rest. Jira issues are matched by status category rather than by project-specific status names, and outbound status changes are applied as workflow transitions.
- Change requests can now track an external issue in any supported tracker, mirroring defects, and record their sync attempts in `change_request_sync_events`.
- `integration_settings.account_email` stores the Jira Cloud account that owns the API token.

### Changed

- The document registry filters, sorts and pages in the database. It used to fetch every document in the project on every visit and narrow the result in the browser - all ten filters, nine sort fields and the paging - so a project with a thousand documents paid for a thousand documents to display thirty. All of it is now query parameters on `GET /api/projects/{ref}/docs`: `status` accepts several values, and `priority`, `reviewer`, `links`, the two date ranges, `sort` and `dir` are new. Free-text search reaches the server once typing pauses instead of re-scanning the table on every keystroke, and matches dates by their ISO form (`2026-03`) rather than by their rendered text.
- The registry listing reads only the columns it returns. It selected whole ORM rows, which meant `description`, `content_json` and `content_html` were read out of Postgres and hydrated for every document on every request, then discarded - none of them are on the listing response. Each type now contributes one arm of a `UNION ALL` of just the shell columns.
- New `GET /api/projects/{ref}/doc-type-summary` returns a count and a suspect-link tally per document type. The project topology draws one node per *type*, never one per document, and the project screen wanted a single SPEC count; both used to download the whole project to work that out, so opening a project fetched every document four times over.
- Every project-scoped table the document registry reads is indexed on `project_id`. Six of the ten had no index that could serve the predicate every screen in Bloom runs, so each request sequential-scanned them: `EXPLAIN` on a forty-project database showed 12,000 rows read and 11,700 discarded to find the 300 that belonged to the project. Documents also take `(project_id, doc_type)`, since that one table backs four document kinds and is always read with both.
- Outbound status mapping is shared by defects and change requests, so change-request statuses (`Implemented`, `Approved`, `Under Review`, …) now open or close the linked issue correctly on GitHub and GitLab as well.
- Upgraded to React 19 and React Router 8, which resolves GHSA-qwww-vcr4-c8h2 (React Router RSC-mode CSRF). The frontend now imports from `react-router` instead of the retired `react-router-dom` package. Frontend builds and CI run on Node 24; Node 22.22 is the supported minimum.
- Upgraded `lucide-react`, whose pinned release declared support only up to React 18.
- The dependency audit no longer carries any reviewed-advisory exception; every advisory now fails the build.
- Coverage measurement was blind to most of the application. SQLAlchemy's async bridge runs endpoint bodies inside greenlets and the test client drives the app from a worker thread, neither of which coverage traces by default, so an endpoint could be exercised by a passing HTTP test and still be reported as entirely unhit. With `concurrency = ["thread", "greenlet"]` the real figure was 71%, not the 63% previously reported. New CRUD coverage across defects, change requests, risks, baselines and project memberships takes it to 82%, and the CI gate moves from 55% to 78%.
- The migration history is collapsed into a single locked baseline of explicit DDL. The base revision previously called `Base.metadata.create_all()`, which meant it always produced whatever the models currently described, so every later revision had to be written with inspect-then-add guards and the real `ALTER` path was never exercised by the fresh-install CI check. The baseline keeps the identifier of the previously deployed head, so an existing database is recognised as up to date and is not re-migrated; no stamp or manual step is required.

### Fixed

- The security headers now reach the pages they were written for. nginx inherits an `add_header` from an outer level only when the current level declares none of its own, so every location that set a `Cache-Control` silently dropped all four - `Content-Security-Policy`, `X-Content-Type-Options`, `Referrer-Policy` and `Permissions-Policy`. That included `location = /index.html`, which is the document the CSP exists to protect and which every deep link resolves to through `try_files`. Checked against nginx 1.24: `/`, `/index.html`, a project deep link, `/runtime-config.js` and `/assets/*` carried none of the four, while `/api/*` carried all four - the policy applied to JSON responses and to nothing else. They now live in `docker/security-headers.conf`, included by the server block and by every location that sets a header, with a test that fails if a location sets one without re-including the file.

- Saving a requirement, test case, design item, risk, change request, or test concept failed with `422`. Their models carry `content_json`/`content_html` and the editor sends them, but the create/update schemas forbid unknown fields and did not declare them, so the editor body could never be persisted or read back. All six now accept and return their rich content.
- API errors are reported with their cause. Validation failures arrive as a list, which the client only handled as a string, so every one surfaced as the opaque "Request failed with status code 422".
- The create screen advertised a hardcoded `-001` identifier that was already taken in any project holding a document of that type. It now shows the identifier the server would actually assign, from the same MAX(suffix)+1 allocation.
- The document type and identifier were rendered twice on the create and edit screens; they now appear once, in the top bar.
- Test case bodies are displayed on the detail page, falling back to the plain description for test cases created before rich content existed.
- Editing a requirement opens the full document editor. It used to render a small inline form with a handful of fields instead, so a requirement could never be edited as a document; the other detail pages already opened the editor. Requirement bodies are also now displayed, falling back to the plain description for requirements created before rich content existed.
- Defects are never opened in the document editor. Their detail page has always edited them in place, but the registry lists defects like any other document, so `docs/defects/{id}/edit` still resolved to the generic editor - which has no severity, resolution summary or tracker link, and would have dropped them on save. Campaigns and test suites are held to the same rule, on create and on edit alike.
- Coverage means the same thing everywhere it is reported. The project card and the dashboard counted a requirement as covered as soon as any test case verified it, while the traceability page - the one whose job is to report coverage - refused to count one whose test cases were all still `Draft`. The stricter reading is now the only one: a draft test case has not verified anything. Projects covered only by draft test cases will read lower than before, and correctly so.
- The coverage gap report no longer advertises `missing_link_types`. The list was never populated, so the branch that produced the `missing_link_types` gap type was unreachable and the field was always empty.
- Clicking an outline entry scrolls to that heading. It resolved the position *before* the heading, which for a top-level heading is the editor's own content element, so every entry scrolled to the top of the document. The outline also follows the reader now: the highlight tracks scrolling rather than only the caret, and keeps itself in view in a long document.
- Every save and delete says whether it worked. Six detail pages each carried their own copy of a toast; everything else reported nothing, or an inline banner that could scroll out of view. The document editor flipped its button to "Saved" for two seconds and, on delete, simply navigated away - indistinguishable from a misclick. Adding or removing a relationship, creating a baseline, editing a project parameter, inviting a user and refreshing an external issue all failed silently. There is now one toast, used by every mutation in the app, and a test that walks the real call sites so a new one cannot skip it.
- Scrollbars follow the theme. Nothing declared `color-scheme`, so the browser painted its default light scrollbars in dark mode; the main content area had no scrollbar styling at all. Both themes are declared now, and every scroll container uses the shared themed scrollbar.
- The editor toolbar keeps up with the document. TipTap 3 stopped re-rendering on transactions unless asked to, and the upgrade did not ask, so the toolbar froze at whatever it showed when the editor opened: Undo and Redo stayed permanently greyed out - Undo was unreachable - and no formatting button ever lit up to show the mark under the cursor.

### Added

- `GET /api/projects/{project_ref}/next-doc-id/{type_code}` reports the next identifier for a document type.
- Relationships are navigable. Clicking a relationship on a document opens the Documents registry filtered to the artefacts sharing that relationship, narrowed to that role and direction. The registry accepts `related_to`, `role`, and `direction`, and shows the active relationship as a filter chip.

### Removed

- The stale duplicate CI workflow and pull request template under `ui/.github/`, neither of which GitHub ever read.

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
