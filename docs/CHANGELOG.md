# Changelog

## 1.2.0 - unreleased

### Added

- Admin company logo on PDF reports: an administrator uploads a company logo in Settings; it renders on the report letterhead (top-left) alongside the EmbedLabs tamper-evidence footer, which is always present. The Settings preview loads through the authenticated client so the admin sees exactly what was stored.
- Markdown document import: classifies a Markdown document into artefacts (by heading tag, front matter, or an at-import marker); a parameter is written inside a sentence as `{{parameter: NAME, value: VALUE}}`, created on import and replaced with `{{NAME}}`, and a name that already exists is never overwritten: the import stops and, for each such name, you keep the project's value or import the file's value under a new name; classified sections are persisted as artefacts; an unlinked imported artefact raises a notification to link it; documented per template. A Markdown mode is added to the Import Wizard.
- Test-case import from CSV and XML, round-tripping with the export, on the `POST /projects/{id}/import` convention; a CSV/XML mode in the Import Wizard.
- Export test cases as Markdown, CSV and XML.
- A `{{` parameter chip shows the parameter's name while a body is edited, with its value on hover, and its value when the body is read; a parameter without a value keeps showing its name. Test-case steps show values the same way when read. The stored document keeps `{{NAME}}`.
- S3-compatible object storage: `STORAGE_BACKEND=s3` keeps attachments in a bucket (AWS S3, MinIO, Hetzner, Ceph) under a per-instance prefix, with the local directory as a mirror that reads fall back to when the bucket does not answer (`STORAGE_LOCAL_MIRROR`, default on). `python -m app.storage migrate --to s3` copies existing files and checks their sizes; cleanup reconciles the bucket; `/api/ready` reports the storage. Local storage stays the default and is unchanged. Adds boto3 to the locked dependencies.
- Groups and policies (admin): a group has members, a policy and project grants, one project or all projects present and future. A policy is an (action x resource) permission matrix; default policies ship, named by what they grant (Administrator, Requirements Manager, Requirements Author, Design Author, Test Author, Approver, Project Administrator, External Reader, Read Only) and protected from deletion. Roles are unchanged: a user's effective permissions on a project are the role baseline plus the policies of their groups granted that project, so a user in no group keeps exactly the access they had. Project-scoped writes, imports, exports, links, parameters and project members are checked against that set; `GET /api/projects/{id}/permissions` returns it, and the UI shows edit controls from it. Managed under Groups & Policies beside Users.
- Migrate test cases from TestRail: `POST /projects/{id}/import/testrail?format=xml|csv` reads a TestRail XML suite or CSV export (separated steps, text steps, preconditions, nested sections, one CSV row per step). CSV columns are detected from the header and can be remapped in the Import Wizard (`POST /projects/{id}/import/testrail/columns`). Each top-level section becomes a test suite, references that match a requirement id become `verifies` links, the rest are kept in the case body with type, priority and estimate, and cases import as Draft. A case keeps `source_ref = testrail:C<id>`, so importing the same export again updates it instead of duplicating it. A From TestRail mode is added to the Import Wizard.
- Address artefacts and their backlinks by public id, not only the database id (additive; database ids continue to resolve).
- Jira to Bloom defects: a Jira issue of a mapped project creates a defect when it matches the project's issue types (default Bug) and optional label, with its description, priority and severity (through a configurable priority map), link and state. The defect then follows the issue (title, description, priority, state; a resolution closes it); a deleted issue leaves the defect marked `Removed in Jira`; a Bloom test-case id in the issue becomes the defect's source. Pull existing issues creates the missing defects from a one-time JQL search. The push to Jira is behind a per-project two-way switch, off by default. Jira is configured in the project's External issue tracker panel; setup is in docs/OPERATIONS.md.
- Open a mentioned artefact, and the exact parameter, from a document body; mention links resolve by public id.

### Fixed

- Requirements and test cases return their editor body.
- A `#` tag shows the current id of the artefact it points at, looked up once per document, instead of the text captured when it was typed; a tag whose target is gone reads as plain text.
- Test-case export and CSV/XML import keep every step row (preconditions, loops, nesting, multi-line text, expected results) instead of flattening them; files exported in the older numbered form still import, and the Markdown export re-imports as the same test cases.

## 1.1.0 - 2026-09-16

### Added

- Cloudron package: `cloudron/CloudronManifest.json` and `cloudron/CloudronVersions.json`; the product image runs under Cloudron's read-only root filesystem with data and generated secrets in `/app/data`; PostgreSQL and local storage addons, mail addon optional; `minBoxVersion` 9.1.0; CI smoke-tests the image against the Cloudron contract.
- First-run setup: `GET /api/setup/status` and `POST /api/setup` create the first administrator; the endpoint answers 409 once any user exists; a confirmation email is sent, best effort.
- `POST /api/campaigns/sync-results` returns the campaigns and the test suites the synced results reached, each with its id, public id, name and page URL; suites carry the number of synced cases they hold and their size.
- Inline artefact tags: `#` in a document body searches the project's artefacts and inserts a link, stored as a `references` link; visible in backlinks, the topology and the registry; excluded from coverage and traceability. Hosted by requirements, designs, risks, change requests, test concepts and the four document kinds.
- Campaign and suite membership is drawn in the topology: `relates_to` campaign → suite, `contains` suite or campaign → test case.
- Jira is supported alongside GitHub and GitLab: mandatory HMAC verification when a webhook secret is set, single-use delivery identifiers, credentials encrypted at rest; issues match by status category; outbound status changes apply as transitions.
- Change requests track an external issue in any supported tracker and record sync attempts in `change_request_sync_events`; `integration_settings.account_email` stores the Jira Cloud account.
- `GET /api/projects/{project_ref}/next-doc-id/{type_code}` reports the next identifier for a document type.
- Relationships are navigable: a relationship on a document opens the Documents registry filtered by `related_to`, `role` and `direction`.
- `GET /api/projects/{ref}/doc-type-summary` returns a count and a suspect-link tally per document type.
- Release pipeline: tested images are promoted by digest to `v1.1.0`, `1.1.0`, `1.1`, `1` and `stable`; a published version is never overwritten; an SBOM is attached to each release.
- CLA acceptance check on pull requests; Dependabot targets `dev`.

### Changed

- A document's links collapse to per-role counts past twenty; a count opens the Documents registry filtered to that relationship.
- The traceability matrix is paginated; its Test Cases and Test Runs columns are removed.
- Artefact identifiers are no longer capped at 999; three digits is a floor.
- Listing projects counts every project in one pass; `artefact_links` and `defects` are indexed on `project_id`; nine per-id lookups are batched.
- The document registry filters, sorts and pages in the database via query parameters on `GET /api/projects/{ref}/docs`, and reads only the columns it returns; every project-scoped registry table is indexed on `project_id`.
- Outbound status mapping is shared by defects and change requests.
- The third role reads "Reviewer" in the interface; the stored value stays `external`.
- The frontend is split by route; the editor loads with the document screens.
- Transactional mail uses Bloom's colours with inlined styles; the setup screen uses Bloom's gradients.
- Coverage measures threads and greenlets; the CI gate is 78%.
- React 19, React Router 8 (`react-router`), Node 24 for builds, `lucide-react` upgraded; the dependency audit carries no exception.
- The migration history is one locked baseline.
- Backend tests are split into `tests/api`, `tests/logic`, `tests/sec` and `tests/pg`; CI runs `tests/pg` twice on the same database.
- Dependencies: alembic 1.19.2, click 8.5.0, cryptography 50.0.1, idna 3.19, pydantic 2.13.5, pydantic-core 2.46.5, uvicorn 0.52.4, wrapt 2.4.0, fonttools 4.64.0, `@tiptap/*` 3.31.3, `@tanstack/react-query` 5.102.8, `@xyflow/react` 12.11.6, `axios` 1.20.0, `react-router` 8.3.1.

### Fixed

- Constraint violations answer 409 or 422 with the request id; unhandled errors return the request id in the body and the message.
- The links panel shows only relationships the open artefact is one end of and drops rows the rule table does not permit; the campaign page no longer shows its test cases' links as its own.
- An unreachable issue tracker answers 502 (connection, DNS, non-issue response) or 504 (timeout).
- Tests no longer load the operator's `.env`; opt in with `BLOOM_TESTS_USE_DOTENV=1`.
- Deleting a user removes its memberships, notifications, import attempts, service credentials, defect assignments and attachment uploads.
- Changing a user to Reviewer works on databases created before the role was renamed.
- The shell stays mounted while a lazy page loads.
- Cloudron mail uses the STARTTLS port; delivery failures return 503 naming host, port and TLS mode; `packageUrl` is removed from the manifest.
- Security headers reach every nginx location that sets `Cache-Control`.
- Requirements, test cases, design items, risks, change requests and test concepts accept and return `content_json` and `content_html`; requirement and test case bodies are displayed; editing a requirement opens the document editor; defects, campaigns and test suites never open in it.
- API validation errors are reported with their cause; the create screen shows the identifier the server will assign; the document type and identifier are rendered once.
- Coverage is counted the same way everywhere: a draft test case verifies nothing; `missing_link_types` is removed from the gap report.
- Outline entries scroll to their heading and the highlight follows scrolling; every save and delete reports its outcome; scrollbars follow the theme; the editor toolbar updates on every transaction.

### Security

- `@tiptap/*` raised past GHSA-cp6q-959q-f8rh; vitest pinned past GHSA-82fw-gwwq-j7x9.

### Removed

- The duplicate CI workflow and pull request template under `ui/.github/`.

## 1.0.0 - 2026-07-24

Initial public beta release of Bloom PLM by EmbedLabs, a product
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
