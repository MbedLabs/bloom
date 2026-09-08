# Changelog

## Unreleased

### Added

- **Artefacts are taggable inline.** A specification lists its requirements in prose, and a reader had no way to reach them other than copying the identifier and searching. Typing `#` in a document body now searches the project's artefacts and inserts a reference that links to the one chosen. Unlike `{{` for parameters and `@` for people, which filter a list handed to the editor as a prop, this one queries the server: a project holds thousands of artefacts, not dozens. Nothing is sent until two characters are typed, results are capped at twenty, and the tag stores the artefact type and its numeric id rather than the display string, so the link survives an identifier widening.

  A tag is written to `artefact_links` with role `references`, which means points at, asserts nothing - so it appears in backlinks, in the topology and in the registry with no new store, and coverage and traceability never see it, since both filter on the exact triple `(TC, REQ, verifies)`. Tags follow their own rule rather than `LINK_RULE_ROWS`: the matrix has no `SPEC -> REQ` row at all, and no `references` role on `REQ -> REQ` or `REQ -> DES`, so constraining the picker by it would have refused the three cases the feature exists for. The matrix stays the sole authority over links, which do assert something and are made deliberately from the links panel.

  Requirements, designs, risks, change requests, test concepts and the four document kinds host tags. Test cases, suites and campaigns are taggable but host none: a container lists its members, so there is no prose to tag in.

- **Campaign and suite membership is drawn in the topology.** The graph built every edge from `artefact_links` alone, but membership lives in `campaign_suites`, `test_suite_items` and `test_campaign_items`, which write no link row - so a campaign rendered as an unconnected node however many suites and test cases it held. `doc-type-summary` now returns membership as type-level edges with counts and the topology merges them with the link-derived ones, following the same roles the rule table gives: `relates_to` for a campaign to its suites, `contains` for a suite or campaign to its test cases. Membership itself stays out of `artefact_links`, so traceability and coverage are unchanged.

### Changed

- **A document's links collapse to counts past twenty.** A well-linked artefact rendered one row per relationship, which is a wall to read, and the number of each kind had to be counted by eye. At twenty the panel shows a count per role and direction instead, and pressing one opens the Documents registry filtered to that relationship, which is already paginated; under twenty it lists rows as before. Twenty counts the document, not each relationship, so eleven `verifies` and nine `references` collapse together. The count is taken after the visibility filter, so a reviewer is never told how many links they cannot open.

### Fixed

- **A campaign claimed relationships it was not part of.** The campaign page fed the links panel from `GET /campaigns/{id}/scope-links`, which returns the links owned by the campaign's *test cases*. The campaign is neither end of those, so the panel invented an orientation for them and each `TC -> REQ verifies` row rendered against the campaign as "verified by TC-xxx" - a traceability claim nobody made. The panel now shows only relationships the open artefact is actually one end of, and drops any row the rule table does not permit for its own pair, so a bad row already in the database stops being displayed as fact.

- **An unhandled error now carries a reference that can be quoted.** A 500 returned Starlette's default response with no detail for the client to extract, so every one of them surfaced as axios's "Request failed with status code 500". The request identifier was already minted per request, stamped on every log line and returned as `x-request-id`, but nothing put it in front of the user, so a report could not be traced to the log line explaining it. The handler now returns that identifier in the body and the message, and the client falls back to the response header when a body carries nothing usable. The exception itself is logged and never returned.

- **Tests no longer inherit the operator's `.env`.** The test configuration loaded the workspace `.env` file, so a developer's real credentials - the production SMTP account among them - were live during a test run, and the suite sent genuine mail. Inheritance is now opt-in behind `BLOOM_TESTS_USE_DOTENV`, off by default, and the test database URL is always overridden.

## 1.0.1 - 2026-09-07

### Added

- **Cloudron packaging.** Bloom installs on a Cloudron box from the same image published for every other deployment; there is no separate Cloudron variant to build, test or keep in step. The manifest requests PostgreSQL and local storage and declares the mail addon optional, and the image runs under Cloudron's read-only root filesystem - application data and generated secrets live in `/app/data`, and everything else that needs writing is redirected to `/tmp` or `/run`, which is a fresh tmpfs on every boot. CI runs a Cloudron compatibility smoke test against the normal image, so the contract is checked on every build rather than at install time. `minBoxVersion` is 9.1.0, the release that introduced community publishing.

- **First-run setup.** An instance with no users offers to create its first administrator. `GET /api/setup/status` reports whether setup is required and `POST /api/setup` creates the account; the endpoint then closes permanently, refusing with 409 once any user exists, and takes a PostgreSQL advisory lock so two browsers racing cannot both succeed. A packaged install has no way to set the environment variables the seeded administrator relied on, and nothing in the Cloudron environment carries user identity - the eight `CLOUDRON_*` variables name domains and origins, not people - so the operator's own address is asked for rather than inferred.

- **A confirmation email after setup.** Setup created the account silently, leaving no record that it had happened. Bloom has no runner enrolment, so the mail is confirmation only and carries no secret. The send is best effort and never fatal: `SMTP_ENABLED` defaults to false under docker-compose and Cloudron's mail addon is optional, so a mail failure aborting setup would leave those installs unable to create an administrator at all.

- Jira is supported alongside GitHub and GitLab, with the same security contract: a configured webhook secret makes HMAC verification mandatory, each delivery identifier is accepted only once, and credentials are encrypted at rest. Jira issues are matched by status category rather than by project-specific status names, and outbound status changes are applied as workflow transitions.
- Change requests can now track an external issue in any supported tracker, mirroring defects, and record their sync attempts in `change_request_sync_events`.
- `integration_settings.account_email` stores the Jira Cloud account that owns the API token.

- `GET /api/projects/{project_ref}/next-doc-id/{type_code}` reports the next identifier for a document type.
- Relationships are navigable. Clicking a relationship on a document opens the Documents registry filtered to the artefacts sharing that relationship, narrowed to that role and direction. The registry accepts `related_to`, `role`, and `direction`, and shows the active relationship as a filter chip.

### Changed

- The traceability matrix is paginated. It listed every requirement in the project at once, and a project runs to thousands of them; it is the one list here whose size is set by the project rather than by a single artefact, which is why the other unpaginated endpoints are left alone - activity and comments are scoped to one artefact and hold tens of rows at most. Adding a skip and a limit alone would have returned the wrong rows: `coverage_status` was computed in Python after loading everything, and both the coverage filter and the coverage sort ran over that list, so page two would have been drawn from a different ordering than page one. Coverage is now derived in the query, from the count of verifying links and how many of those test cases are past Draft, so the filter, the sort and the page all agree. The response is the same `PaginatedResponse` the other eleven list endpoints return.

- Artefact identifiers are no longer capped at 999. A project could hold at most 999 requirements, or test cases, or any single artefact type; the thousandth creation raised a bare `ValueError` that reached the caller as a 500 with no explanation, and deleting a row did not free the number, because the next identifier is MAX+1. Three digits is now a floor rather than a ceiling, and crossing the boundary rewrites the identifiers already stored in that project and type, so `FLT-REQ-001` becomes `FLT-REQ-0001` when `FLT-REQ-1000` appears. Equal width is the point: mixed widths sort wrongly as strings, with `FLT-REQ-1000` landing before `FLT-REQ-002`. Links are unaffected, since `artefact_links` joins on numeric primary keys and never on these strings.

- Listing projects counts every project in one pass. It computed eleven counts per row by calling a helper that issues ten queries, so a ten-project dashboard cost 101 sequential statements, each waiting on the last. Each artefact type is now counted once across every project with a `GROUP BY`, and coverage likewise, so the query count no longer depends on how many projects are listed. The single-project helper is untouched and still serves the detail endpoints. New tests compare the batched counts against the per-project endpoint, check the two do not bleed between projects, and assert the statement count does not grow with the number of projects, so the N+1 cannot return quietly.

- Two tables gained an index able to serve `WHERE project_id = ?`. `artefact_links` is the traceability table and the one that matters: it had four single-column indexes and a unique constraint starting on `source_type`, but nothing leading on `project_id`, and `role` only as that constraint's fifth column. The coverage query filters `project_id`, `source_type`, `target_type` and `role` together, so it gets one composite in that order, and `EXPLAIN` now shows an index scan with all four as the index condition rather than a filter. `defects` had only its primary key, despite an earlier revision's note claiming otherwise.

- Nine paths that issued one statement per requested id are batched, so their cost is flat rather than proportional to the size of the request: validating suites and collecting their test cases on campaign create and update, validating test case ids on suite create, counting sections per listed document and loading each section being reordered, loading the parent document of every matched section, and loading each requirement and test case being imported. An import of several hundred rows meant several hundred round trips; each is now a single `IN` or `GROUP BY`. New tests pin the behaviour the collapsed queries could silently drop - the offending suite id still named in the 404, a suite belonging to another project still rejected, unknown test case ids still ignored silently, and section counts still attached to their own document.

- The frontend is split by route. Every visit downloaded, parsed and executed 1.7 MB of JavaScript in a single chunk before anything rendered - including the login screen, which needs none of it, and 19 TipTap and ProseMirror packages reachable only from the document screens. The entry chunk is now 404 KB (121 KB gzipped), with the editor in its own 708 KB chunk that arrives only when a document is opened. The auth screens stay eager: they are the first paint and are usually opened straight from an email link, so a spinner there would trade a visible regression for a negligible saving. A test imports every declared lazy path and asserts a component comes back, since `lazy(() => import(...))` is not checked the way a static import is.

- Transactional mail is sent in Bloom's own colours. Every template was hardcoded to `#1a73e8`, so both products sent identical Google-blue mail that matched neither of them. The palette is derived from the same HSL tokens `index.css` already defines, so the mail cannot drift from the product it came from. Copy is unchanged; only the shell was replaced, and its styles are inlined rather than kept in a `<style>` block, because several clients - Gmail among them - drop or rewrite head styles on forwarded mail, which left the buttons unstyled.

- The third role reads **Reviewer** in the interface: the badge on the users table, both role selectors, and the document visibility picker beneath them. Only the labels change - the stored value is still `external`, and the API contract, the database enum and every role check are untouched. A reviewer may well be internal, but the capability is identical either way, project-scoped and read-only, so one role covers both. Unrelated uses of the word keep their names: External Standard as a document type, the external issue tracker, and the external-link icon do not refer to this role.

- The Test Cases and Test Runs columns are gone from the traceability matrix. Neither belongs in it: the matrix answers whether a requirement is verified, and listing the individual test cases and their executions is a different question, answered on the requirement and campaign screens. Test Runs also carried nothing, rendering an em dash on every row unless a run happened to be linked, beside a Coverage verdict computed without ever consulting it. Coverage and Impact are untouched, and the gap list further down still shows linked test cases, because that section is about what is missing rather than about the trace table.

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

- Deleting a user answered 204 and changed nothing. The handler cleared user tokens, invitations and the requirement and test case review columns, but not the memberships, notifications, import attempts, service credentials, defect assignments or attachment uploads that also reference `users.id` - and project memberships cover every user who can do anything. The foreign key violation surfaced during the session commit, which runs after the handler returned, so the 409 the handler defines never fired, the transaction rolled back, and the caller had already been told it worked. Those references are now cleared, with the reviewer document allowlist removed before the membership it hangs off, and the session is flushed inside the handler - so any future reference to `users.id` fails loudly as a 409 instead of quietly rolling back behind a 204. Service credentials are reassigned to the deleting administrator rather than removed, because one outliving whoever minted it is normal and dropping it would break a working integration.

- Changing a user to Reviewer returned 500 on any database created before the role was renamed: the application was renamed but the PostgreSQL enum was not, so the driver rejected the label outright. The enum is rebuilt through text, which moves any surviving `reviewer` rows across in the same transaction - `ALTER TYPE ... ADD VALUE` cannot be used in the transaction that writes the new label. The revision no-ops where the value already exists, so databases built from the locked baseline are untouched. Verified against a fixture reproducing the old schema.

- The setup screen is styled with Bloom's own gradients. It was authored from Bud's and kept Bud's class names, which exist only in Bud's Tailwind config, so Bloom emitted no CSS for either - silently, since Tailwind ignores names it does not know. The page lost its backdrop and the submit button rendered with no background at all, while build, lint and tests all stayed green. A new test walks the UI for gradient utilities and asserts each is defined in that app's config.

- The shell stays mounted while a lazy page loads. The Suspense boundary added with route splitting wrapped the whole route table, so any lazy page unmounted the sidebar and header while it loaded and the entire shell flashed on every navigation. It now sits at the layout's outlet and suspends only the routed content.

- Mail on Cloudron. The packaging pointed `SMTP_PORT` at `CLOUDRON_MAIL_SMTP_PORT` (2525) while also setting `SMTP_STARTTLS=true`, but the relay offers STARTTLS only on `CLOUDRON_MAIL_STARTTLS_PORT` (2587); 2525 is plaintext and answers a STARTTLS command with "extension not supported". Probing the relay confirms it - 2525 no STARTTLS, 2587 STARTTLS, 2465 implicit TLS - so the port and the TLS mode are now chosen together, preferring the encrypted port.

- Mail transport failures are diagnosable. Every endpoint that sends mail catches `MailConfigurationError` and returns a 503 carrying the message, but nothing caught transport errors, so a failed invitation came back as a bare 500 with an empty body - no indication that mail was even involved. `send_email` now translates `smtplib` and socket failures into `MailDeliveryError`, naming the host, port and TLS mode alongside the underlying error. It subclasses `MailConfigurationError`, so all seven existing handlers pick it up unchanged, covering invitations, resends, password resets, verification and email changes at once.

- `packageUrl` is gone from the Cloudron manifest. Cloudron 9.2.0 rejects the whole manifest with "must NOT have additional properties" when it is present, so the app could not be installed at all. The packaging documentation lists it as a valid optional property, but the schema the box actually enforces does not accept it; probing every documented property against that schema, it is the only one rejected. `documentationUrl` already points at the repository.

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

### Security

- TipTap is raised past GHSA-cp6q-959q-f8rh (moderate), in which `mergeAttributes()` turns an own `__proto__` key into inherited executable DOM attributes, affecting every package in the family below 3.30.4. The declared range already allowed the fix, but the lockfile was held at 3.28.0 and neither an audit fix nor an update would cross the minor, so the range is raised explicitly; it resolves to 3.31.0.

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
