# Changelog

## 1.3.0 - unreleased

### Added

- Assign a person to several policy groups in one project. Their effective access combines the assigned groups within the existing policy scopes; removing one membership retains the others.
- User Management shows, under each user, the groups that user belongs to and each project they can access with the groups behind it; the list stays collapsed until it is opened for that user.
- Every project's issue tracker syncs by itself, every 15 minutes by default (`INTEGRATION_SYNC_MINUTES`, `0` turns it off), with no webhook needed. Matching Jira issues become defects, including those already open when the integration is set up; linked Jira issues carry their changes and deletions onto their defects and change requests; linked GitHub and GitLab issues carry their state. Sync now runs the whole Jira sync at once.
- The project's External issue tracker panel shows when the tracker last synced, what that sync created and updated, the repositories it skipped and why a sync failed, and refreshes every minute. Its Jira button, Sync now, runs the whole sync at once.
- The review panel of a controlled document shows who created it and its assignee, and lets the creator, the assignee and whoever may assign the reviewer choose another assignee.
- Select a passage of a document to comment on it: the passage is highlighted and its thread sits level with it in the comments column; general comments and threads whose passage changed open from the top of the column. Threads take replies, can be resolved and reopened, and resolved ones show on request. The person editing a document sees its open threads beside the editor.
- Visions, a new project document type (`VIS`, ids such as `PRJ-VIS-001`), for an idea that becomes binding once approved. A vision is reviewed, approved and revised like a specification. Requirements and specifications derive from it, change requests and risks affect it, it refers to standards, and its text takes tags like every document. The new built-in Visions policy belongs to the Product Owners group and to project access that holds every released document and project policy; the built-in read, review and administration policies cover visions as they cover specifications, and policies made by an administrator are unchanged. Markdown import files a `vis` or `vision` section as a vision. Baselines record visions in a section of their own. Visions come first in the project sidebar, the project overview, the registry filter and the topology, are written in the full document editor, and show Idea until approved and Binding once the viewer can see that a vision was approved.
- The audit log records every API call, from the browser, the CLI and MCP sign-in, service credentials and scripts, health probes, metrics scrapes and CORS preflight requests included, as an `api.request` event with the actor, whether a user token came from the CLI or the browser, the service credential, the method, route, path, status, duration, the names of the query parameters, the credential kind presented and the id and document ID of what a call created. 401, 403, 429, a 404 for something that exists but the caller may not see and any 404 answered to an anonymous caller are recorded as `denied`, a deactivated account's refused request names that account, and 20 denied requests from one address within 10 minutes (`AUDIT_REFUSAL_THRESHOLD`, `AUDIT_REFUSAL_WINDOW_MINUTES`) leave one `security.repeated_refusals` event. `GET /api/audit` filters by actor type, address, request id and HTTP status. No body, header value, query value, password or token is stored.

### Changed

- Every collection of a document type is named in the plural, with the names of the project sidebar: Designs in the sidebar and on the project overview, and Requirements, Designs, Changes, Standards, Test Campaigns and the others on the dashboard count tiles, the topology, the breadcrumbs, the policy editor rows and the link target picker and its search. One record keeps its singular name.
- A controlled document has an assignee, at first its creator; the creator, the assignee and whoever may assign the reviewer hand it to another person who can see and edit it. The assignee requests review. Besides the reviewer, the creator, the assignee and the approver comment until the document is approved, and each comment notifies the others with a link to the document.
- A linked GitHub, GitLab or Jira issue changes its defect's status only when the issue closes, which closes the defect, or when a closed issue is open again, which sets the Closed defect back to Open. Statuses set in Bloom stay otherwise, also a defect closed or reopened in Bloom while its issue stays as it was, and the issue's state still shows on the defect.
- A document with rich text is reviewed beside its text: a comments column takes the place of the side panel from 1024 pixels wide and sits above the text on narrower screens; the review state and the actions the viewer can take sit in one line above the text, with the assignment and revision history behind Details, and the other side-panel cards follow the text. Reports, standards and other documents without rich text, suites, campaigns and defects keep their side panel with the discussion first.
- Every email carries the product identity as its heading and one action. Access request and workflow request emails also open their plain text with the identity and give a product-specific next step in HTML and plain text. Workflow request emails are sent in HTML as well as plain text.
- The product identity is fixed as Bloom PLM by EmbedLabs across the application, emails and API. The sidebar shows Bloom PLM with by EmbedLabs beneath it. The `BLOOM_APP_NAME` setting is removed; an existing environment variable or `.env` entry with that name is ignored.
- The invitation and email change dialogs close with Escape and put the focus on their first field when they open. A project card opens with the keyboard as well as with the mouse.
- A source install needs Python 3.11 or later.
- The container starts as root only to prepare its directories, data ownership and, on Cloudron, its secrets and migrations; supervisord, nginx and uvicorn then run as `appuser`. Kubernetes `runAsNonRoot` policies are not supported.

### Fixed

- Line spacing in the document editor is set per paragraph and heading, list items, quotes and table cells included, and is saved with the document, so it shows the same after reopening, on the reading page and in approved revisions. The menu offers Single, 1.5 and Double as multiples of the normal spacing and marks the spacing at the cursor.
- Administrator welcome emails confirm the account is ready and give product-specific next steps, with matching HTML and plain-text instructions. The obsolete one-time runner registration key instructions are removed.

### Security

- Pillow raised to 13.0.0, certifi to 2026.10.19, dnspython to 2.9.0, follow-redirects to 1.16.1, vitest to 4.1.12 and zod to 4.6.7, the patched releases.

## 1.2.0 - 2026-10-17

### Added

- Readers request reports beside linked Bud runs and follow Pending, Delivered or Refused state. Bud publishers receive requests through the existing integration connection; successful report delivery provides a document link subject to existing project visibility.
- Upload and remove your profile picture in Settings; show it alongside users, comments and activity.

- Admin company logo on PDF reports: an administrator uploads a company logo in Settings; it renders on the report letterhead (top-left) alongside the EmbedLabs tamper-evidence footer, which is always present. The Settings preview loads through the authenticated client so the admin sees exactly what was stored.
- Markdown document import: classifies a Markdown document into artefacts (by heading tag, front matter, or an at-import marker); a parameter is written inside a sentence as `{{parameter: NAME, value: VALUE}}`, created on import and replaced with `{{NAME}}`, and a name that already exists is never overwritten: the import stops and, for each such name, you keep the project's value or import the file's value under a new name; classified sections are persisted as artefacts; an unlinked imported artefact raises a notification to link it; documented per template. A Markdown mode is added to the Import Wizard.
- Test-case import from CSV and XML, round-tripping with the export, through `POST /projects/{id}/import/test-cases?format=csv|xml`; every step row (preconditions, loops, nesting, multi-line text, expected results) is kept; a CSV/XML mode in the Import Wizard.
- Export test cases as Markdown, CSV, XML and PDF, with every step row; the Markdown export re-imports as the same test cases.
- More PDF reports on the report letterhead: the traceability matrix, the test cases, and a verification dossier (each requirement with the test cases that verify it, their last results and the linked runs). Every project export and report is offered from one Export menu on the traceability page. A requirement lists the Bud runs linked to it; each opens in Bud, where the user signs in with their own Bud account and downloads the run report. An export holds only what the user may see: artefacts hidden from external users and document types outside their allowlist are left out.
- A `{{` parameter chip shows the parameter's name while a body is edited, with its value on hover, and its value when the body is read; a parameter without a value keeps showing its name. Test-case steps show values the same way when read. The stored document keeps `{{NAME}}`.
- S3-compatible object storage: `STORAGE_BACKEND=s3` keeps attachments in a bucket (AWS S3, MinIO, Hetzner, Ceph) under a per-instance prefix, with the local directory as a mirror that reads fall back to when the bucket does not answer (`STORAGE_LOCAL_MIRROR`, default on). `python -m app.storage migrate --to s3` copies existing files and checks their sizes; cleanup reconciles the bucket; `/api/ready` reports the storage. Local storage stays the default and is unchanged. Adds boto3 to the locked dependencies.
- Access management: a group is a set of policies. Assign people to a policy group separately in each project. Administrators, Developers, Product Owners and Testers are available in every project; Customers is optional. Policies control actions by resource and document origin; Write includes Read, while Review remains independent. Read Internal covers all origins; Read Customer and Review Customer cover customer content. Application Administration and Access Management are assigned separately from project access. Default policies are protected and can be duplicated; groups remain editable.
- Custom origins (stored as tags): the Access Management application permissions control the origin catalogue. An artefact editor assigns origins from their permitted scope on the detail page, and policies can restrict access by origin. Viewer (`external`) accounts choose origins only when creating an artefact; they cannot change them afterwards. Renaming is available through `PATCH /tags/{id}`, rather than a rename control in the web app, and preserves references from artefacts and policies.
- Controlled documents start in Draft. Their creator requests review, the assigned reviewer comments and requests approval, and an eligible approver records approval. Requests produce notifications and email. Approved content is preserved when edited; a new linked approved CHG advances Version and Revision on Save. A correction without a new CHG returns to Draft at the same numbers. Approved CHGs cannot be edited. Risks, defects, campaigns, reports and standards retain their operational lifecycles.
- Migrate test cases from TestRail: `POST /projects/{id}/import/testrail?format=xml|csv` reads a TestRail XML suite or CSV export (separated steps, text steps, preconditions, nested sections, one CSV row per step). CSV columns are detected from the header and can be remapped in the Import Wizard (`POST /projects/{id}/import/testrail/columns`). Each top-level section becomes a test suite, references that match a requirement id become `verifies` links, the rest are kept in the case body with type, priority and estimate, and cases import as Draft. A case keeps `source_ref = testrail:C<id>`, so importing the same export again updates it instead of duplicating it. A From TestRail mode is added to the Import Wizard.
- Resolve artefact detail references by public id; existing database identifiers continue to resolve.
- Jira to Bloom defects: a Jira issue of a mapped project creates a defect when it matches the project's issue types (default Bug) and optional label, with its description, priority and severity (through a configurable priority map), link and state, reported by the Bloom user behind the integration's account email. The defect then follows the issue (title, description, priority, state; a resolution closes it); a deleted issue leaves the defect marked `Removed in Jira`; a Bloom test-case id in the issue becomes the defect's source. Pull existing issues creates defects for the issues still open, from a one-time JQL search. The account email and API token are checked with Jira first, and a classic API token or an API token with scopes (read:jira-work, read:jira-user, and write:jira-work for two-way sync) works; a token with scopes is used through Atlassian's API gateway for the site. A credential Jira does not accept is reported instead of an empty search. The push to Jira is behind a per-project two-way switch, off by default. Jira is configured in the project's External issue tracker panel; setup is in docs/OPERATIONS.md.
- Open a mentioned artefact, and the exact parameter, from a document body; mention links resolve by public id.
- Audit log: security-relevant events (authentication, accounts, project members, external document types, groups, policies and artefact visibility, configuration, deletions, exports, imports, attachments) are recorded with the acting user, the request id, the client address, the outcome and details without secrets; a failed sign-in is recorded although the request fails. Administrators read it under Audit log (`GET /api/audit`, filtered by actor, action, target, project, outcome and time). No endpoint changes or deletes an event; `python -m app.audit prune --older-than-days N` removes old events on the operator's schedule. Event times are shown in the viewer's time zone.
- Access-denied page: a signed-in user who opens a project, document, artefact, suite or campaign they may not see gets one page that names it only by the address (public id and project), with a Request access button. The administrators are emailed with the requester, the resource, the time, the request id and a link to the project's members; one request per user and resource per 24 hours, and the page says when one is pending. Administrators mark a request granted or refused under Access, Requests across projects or on the project's members page; project access is managed separately. The request and the decision are recorded in the audit log. A mail failure is reported to the user and the request is kept.

### Changed

- Project members and document attachments use vertical three-dot action menus. Member removal and attachment download/removal retain their existing permissions.
- A read by id of an artefact in a project the user is not in answers 404, as for an artefact the user may not see (was 403).
- Times shown to people stop at the minute: dates and times in the web app, the CSV exports of requirements and test cases, the summary of a published Bud report, and the time in access-request emails (in UTC).

### Fixed
- Refresh document lists, project counts, link labels, traceability and reports after successful project changes; remove deleted detail caches after navigation without fetching deleted records.

- Signing out, and a session check that fails while a user is signed in, now reload the page, and a tab reloads when it next renews its session and finds it belongs to another user signed in from another tab. Nothing cached for the previous user stays in memory, and signing in empties the cache as well. Before, the next user in the same tab could be shown data cached for the previous one for up to five minutes.
- A database created before the locked migration baseline gets `integration_settings.account_email` and the `change_request_sync_events` table it lacked; the integration settings no longer answer 500 on such an instance.
- A database error while committing a request, such as a constraint violation, is answered with 409 or 500 and the request id; the commit now runs before the response is built instead of after it had started.
- Requirements and test cases return their editor body.
- A `#` tag shows the current id of the artefact it points at, looked up once per document, instead of the text captured when it was typed; a tag whose target is gone reads as plain text.
- Test execution times reported by a results sync were stored in the server's time zone instead of UTC, so a server not running in UTC stored and showed them shifted by its offset.
- User, project member, document, integration setting, sync event, notification and service credential timestamps in API responses carry the UTC marker (`Z`); without it the Users page showed the time of an email change request shifted by the viewer's UTC offset.
- Creating a specification, protocol, report or standard from the web app answered 422 and created nothing, because the create page sends the first status and the API refused the field. A document create now accepts `status` when it is `Draft`, the status a new document starts in; any other first status is refused with 422.

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
