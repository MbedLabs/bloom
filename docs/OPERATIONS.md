# Operating Bloom

A practical guide for running Bloom in production: monitoring, logs, backup and
restore, upgrades, and disaster recovery. Runtime configuration lives in
environment variables (see [`.env.example`](../.env.example) for the full list).

## Image tags

Images are published to `ghcr.io/mbedlabs/bloom`:

| Tag | Moves? | Use for |
|---|---|---|
| `sha-<commit>` | immutable | exact reproducibility / debugging |
| `1.2.3` (full semver) | immutable | **production: pin this** |
| `1.2`, `1` | moving (stable releases) | tracking a minor/major line |
| `stable` | moving → newest stable release | low-maintenance production |
| `latest` | moving → newest `main` build | **development / staging only** |

Set `BLOOM_VERSION` in `.env` to a pinned version (e.g. `1.2.3`) or `stable`.
Never run `latest` in production: it is the rolling development build. `stable`
starts existing once you publish your first `vX.Y.Z` release tag.

## Health checks

- `GET /api/health`: **liveness**. Confirms the web process responds; it does not
  query PostgreSQL, so it never claims a database connection it has not verified.
- `GET /api/ready`: **readiness**. Runs `SELECT 1` against PostgreSQL and returns
  `200` only when the database is reachable, `503` otherwise. This is what the
  container `HEALTHCHECK` and `docker-compose` healthcheck probe, and it is the
  right target for load-balancer / orchestrator readiness checks.

## Logs

Bloom writes logs to stdout so any container log driver or shipper picks them up.

| Variable | Default | Meaning |
|---|---|---|
| `LOG_LEVEL` | `INFO` | Root log level (`DEBUG`, `INFO`, `WARNING`, ...) |
| `LOG_JSON` | auto | `true`/`false`. Unset: JSON in production (`BLOOM_ENV=production`), text otherwise |

JSON mode emits one object per line:

```json
{"ts": "2026-07-17T02:00:00+0000", "level": "INFO", "logger": "bloom.access",
 "message": "GET /api/health 200 1.2ms", "request_id": "6f6e...",
 "method": "GET", "path": "/api/health", "route": "/health",
 "status": 200, "duration_ms": 1.2}
```

Every response carries an `X-Request-ID` header. Incoming `X-Request-ID`
values are propagated, so you can trace a request across a reverse proxy,
Bud, and your log aggregator. Pass the header from your edge (nginx:
`proxy_set_header X-Request-ID $request_id;`) for end-to-end correlation.

## Metrics (Prometheus)

- `GET /api/metrics`: Prometheus text format.
- `http_requests_total{method,path,status}`: request counts by route template.
- `http_request_duration_seconds{method,path}`: latency histogram.
- Plus standard Python process/GC metrics.

Scrape config:

```yaml
scrape_configs:
  - job_name: bloom
    metrics_path: /api/metrics
    static_configs:
      - targets: ["bloom.example.internal:8080"]
```

The endpoint is unauthenticated (the Prometheus convention). Either keep it
reachable only from your monitoring network, or disable it entirely with
`ENABLE_METRICS=false`.

## Backup and restore

Bloom has two stateful locations: **PostgreSQL** for records and the
**attachment directory** (`BLOOM_ATTACHMENT_DIR`, `/app/attachments` in the
supplied Compose deployment) for document evidence. Compose persists the latter
in the `bloom-attachments` named volume. Back up and restore both at the same
point in time so attachment rows and files stay consistent.

Nightly backup (adjust connection details to your deployment):

```bash
# database
pg_dump --format=custom --file="bloom-$(date +%F).dump" "$DATABASE_URL"

# document evidence; use your named-volume or host-volume backup tooling
tar czf "bloom-attachments-$(date +%F).tgz" -C /path/to/attachments .
```

Restore:

```bash
pg_restore --clean --if-exists --no-owner --dbname "$DATABASE_URL" bloom-YYYY-MM-DD.dump
tar xzf bloom-attachments-YYYY-MM-DD.tgz -C /path/to/attachments
```

Verify after restore: `GET /api/ready` (confirms the database is reachable),
then log in and confirm projects, requirements, traceability views, and a sample
attachment download all work.

## Attachment upload controls

`BLOOM_MAX_ATTACHMENT_SIZE` defaults to 25 MiB per file and
`BLOOM_MAX_DOCUMENT_ATTACHMENT_BYTES` defaults to 250 MiB per document. Bloom
also preserves `BLOOM_MIN_ATTACHMENT_FREE_BYTES`, validates an allowlist of
MIME types, streams through a temporary file, and atomically promotes only a
complete upload.

Interactive document uploads default to ten starts per authenticated user in a
rolling fifteen-minute window and one active upload per user. Configure these
with `BLOOM_ATTACHMENT_UPLOADS_PER_15_MINUTES` and
`BLOOM_MAX_CONCURRENT_ATTACHMENT_UPLOADS_PER_USER`; concurrency is deliberately
fixed at one. Automated Bud report publishing uses a scoped service credential
and remains separate from the human request allowance, while retaining the
same file, document, MIME, and disk-capacity checks.

These controls limit resource exhaustion; they are not a malware scanner.

## Markdown import

The document format, one example per artefact type and how to write such a document
with an AI assistant are in `docs/md-import-format.md`.

## Jira defects

A Jira project can feed a Bloom project: a matching Jira issue creates a defect, and
the defect then follows the issue. The direction is Jira to Bloom unless the project
turns on two-way sync, which also pushes defect title and status changes to Jira.

Each project has its own Jira integration. The instance needs
`INTEGRATION_ENCRYPTION_KEY` set first; without it Bloom refuses to store the
integration.

In Bloom, as an administrator, open the project settings, choose Jira under External
issue tracker and fill in:

- Site URL (`https://your-site.atlassian.net`).
- The account email and API token of a Jira account (created under
  id.atlassian.com, Security, API tokens). The automatic sync, Sync now and two-way
  sync need them, and the email also makes that Bloom user the reporter of the
  defects. Webhook deliveries need neither. They are stored for this project only, encrypted. Both kinds of token work:
  a classic API token acts with the account's own Jira permissions; an API token with
  scopes needs `read:jira-work` and `read:jira-user`, plus `write:jira-work` for
  two-way sync, and Bloom calls Jira for it through Atlassian's API gateway for the
  site. Bloom checks the credential before each sync or push and reports a token Jira
  does not accept.
- Webhook secret: any long random string; the same value goes into Jira.
- Jira project key, issue types (default `Bug`), and optionally a label, a custom field
  that holds Bloom test-case ids, and extra JQL used by the sync.
- The Jira priority to Bloom priority map.

The webhook is optional: the automatic sync below works without it. With a webhook,
changes arrive within seconds. In Jira, as a site administrator, open Settings, System,
WebHooks and create a webhook:

- URL: `https://<bloom-host>/api/integrations/jira/webhook`
- Secret: the webhook secret entered in Bloom. Jira signs each delivery with it and
  Bloom rejects unsigned or wrongly signed deliveries.
- Events: Issue created, updated and deleted. A JQL filter such as `project = PROJ`
  keeps the events of other projects away.

What Bloom does with an event:

- Created or updated, for an issue with no defect yet: a defect is created when the
  issue matches the project's issue types and label. It takes the summary, the
  description as text, the priority (also as severity) through the map, the issue URL
  and state. A Bloom test-case id of the project in the summary, the description or
  the reference field becomes the defect's source.
  The defect's reporter is the Bloom user whose email is the integration's account
  email; with no such user it has no reporter.
- Updated, for a linked issue: title, description, priority and state follow Jira. A
  resolution or a Done status closes the defect; a closed issue open again sets the
  Closed defect to Open. Other Bloom statuses stay as set in Bloom. A change request
  closes when its issue closes; the automatic sync closes only one still Submitted and
  records the issue state on the others.
- Deleted: the defect stays and its issue state reads `Removed in Jira`.
- A delivery Jira retries with the same identifier is processed once.

## Automatic tracker sync

Bloom syncs every enabled tracker integration by itself, every
`INTEGRATION_SYNC_MINUTES` minutes (default 15; `0` turns it off). It needs no
webhook and no public URL. One replica syncs a given project at a time.

- Jira, with the site URL, account email, API token and Jira project key set: the
  first run, and the first run after each save of the integration, searches the
  saved filter for every open matching issue (Done issues excluded) and creates the
  defects that do not exist yet, when "Create a defect for each new matching issue"
  is on. Later runs search only the issues changed since the last run. Linked defects
  and change requests follow their issue as with a webhook update. Each run also
  checks up to 50 linked issues for deletion; an issue Jira no longer returns reads
  `Removed in Jira`.
- GitHub and GitLab, with a token set: the state of the issues linked to defects and
  change requests follows the tracker; a closed issue closes its defect, and a closed
  issue open again sets the Closed defect to Open. Other Bloom statuses stay as set in Bloom. A repository
  the token cannot read is skipped and named on the panel; a rate limit or an outage
  fails the run, which is retried on the next interval.

Searches return at most 1000 issues per run; a larger backlog continues on the next
run. The tracker panel shows the last sync, its counts and its error. Sync now, on
the Jira panel, runs the whole Jira sync at once and creates defects whether or not
the inbound creation option is on. All of it only reads from the tracker.

## Object storage (S3)

Attachments are kept in `BLOOM_ATTACHMENT_DIR` by default. To keep them in an
S3-compatible bucket (AWS S3, MinIO, Hetzner, Ceph) instead:

- `BLOOM_STORAGE_BACKEND=s3` and `BLOOM_S3_BUCKET`. The bucket must exist.
- `BLOOM_S3_ENDPOINT_URL` for anything that is not AWS (for MinIO, for example
  `http://minio:9000`); `BLOOM_S3_REGION` where the store needs one.
- `BLOOM_S3_PREFIX` (default `bloom`) keeps several instances apart in one bucket.
- `BLOOM_S3_ACCESS_KEY_ID` and `BLOOM_S3_SECRET_ACCESS_KEY`, or neither, in which
  case the ambient AWS credentials (an instance role) are used.
- `BLOOM_STORAGE_LOCAL_MIRROR` (default `true`) also keeps every file in
  `BLOOM_ATTACHMENT_DIR`. Reads come from the bucket and fall back to the mirror when the
  bucket does not answer; the log then names the key as a warning. The free-space
  reserve applies to this directory; quotas in the bucket are the operator's.

Existing files are copied with `python -m app.storage migrate --to s3`. Each file
keeps its storage name under the prefix, sizes are checked after the copy, and files
already in the bucket are skipped, so the command can be run again. The local files
stay where they are.

`GET /api/ready` reports `storage`: `local`, `s3`, or `s3-unreachable` when the bucket
did not answer. It stays `200` in that case, because the database decides readiness
and reads can still come from the mirror. Orphan cleanup lists the bucket; a file is
counted missing when the bucket lacks it. On Cloudron the variables are set with
`cloudron env set`; keep the mirror, as it lives under `/app/data` and is part of
Cloudron's backup.

## Audit log

Every HTTP request is recorded in the `audit_events` table as one `api.request` event, written when the response is finished: every call from the browser, the CLI and MCP sign-in, service credentials and scripts, health probes and metrics scrapes included, and every refused attempt. The event names the actor (a user, `service` or `anonymous`), the request id, the client address and user agent, and holds in its details: `method`, `route` (the template, such as `/api/requirements/{requirement_id}`), `path`, `status`, `duration_ms`, `query` (the names of the query parameters, never their values), `auth` (`bearer` when a bearer token was presented, else `none`), `client` (`cli` for a CLI or MCP sign-in token, `web` for any other user session), `service_credential_id` for a service credential, and for a `201` answer `created_id` (the `id` of the answer, or its `document_id`) and `created_doc_id` (such as `PRJ-REQ-001`) of the created object. The target is the last path parameter ending in `_id` and the project the `project_id` path parameter. The outcome is `success` below `400`; `denied` for `401`, `403`, `429` and a `404` for an artefact the user may not see; `failure` for any other status from `400`. No body, header value, query value, password or token is ever stored. A failure to write the event is logged and never changes the response.

When one client address has `AUDIT_REFUSAL_THRESHOLD` (default `20`) denied requests within `AUDIT_REFUSAL_WINDOW_MINUTES` (default `10`), one `security.repeated_refusals` event is written with the address, the count and the window, at most once per address per window.

Security-relevant events are also written as events of their own in the same transaction as the action: sign-in, sign-out, session refresh, password change and reset, email verification and email change; user creation, invitation, role change, activation, deletion; project members, external document types, groups, policies and artefact visibility; configuration changes; deletions, exports, imports and attachments. A failed sign-in or password reset is recorded even though the request itself fails. Each event carries the acting user or `anonymous`/`service`/`runner`, the action, the target, the request id (the `x-request-id` response header), the client address and user agent, the outcome and details without secrets.

Administrators read the log under Audit log in the sidebar, or with `GET /api/audit` (filters: `actor_user_id`, `actor_type`, `action` or an action prefix ending in `.` such as `api.`, `target_type`, `target_id`, `project_id`, `outcome`, `ip`, `request_id`, `status` (the HTTP status of an `api.request` event), `since`, `until`, `limit`, `offset`). No endpoint changes or deletes an event.

The client address is the one the image's own nginx received. Behind another reverse proxy (Cloudron, a load balancer) it is that proxy's address.

Access requests are emailed to every active administrator through the transactional mail settings above; without SMTP the request is still recorded and shown under Access, Requests and on the project's members page, and the user is told the email could not be sent.

Retention is the operator's choice. The application never deletes events; to remove old ones, run on a schedule:

```
python -m app.audit prune --older-than-days 365
```

## Upgrades

1. Back up first (see above).
2. Pull the target image: `docker pull ghcr.io/mbedlabs/bloom:<version>`.
3. Run migrations before serving traffic: `alembic upgrade head`
   (run inside the new image against the production `DATABASE_URL`).
4. Restart the container. Confirm `/api/ready` returns `200` and check the
   version shown in the UI.

When upgrading to `1.0.0`, migration `d20260722a06` clears legacy plaintext
GitHub/GitLab tokens and webhook secrets and disables the affected tracker
integrations. Configure `INTEGRATION_ENCRYPTION_KEY`, re-enter rotated
credentials, and explicitly enable those integrations again.

Rollback: restore the pre-upgrade database dump and start the previous image
tag. Never run a newer schema against an older application version.

## Disaster recovery

- **RPO** equals your backup cadence: nightly dumps mean up to 24h of loss;
  schedule to your tolerance and copy backups off the host.
- **RTO** is dominated by Postgres restore time; rehearse the restore path
  against a scratch database at least once before you depend on it.
- Keep `SECRET_KEY`, optional `SERVICE_TOKEN_PEPPER`, optional
  `INTEGRATION_ENCRYPTION_KEY`, and SMTP credentials in your secret store. A
  different `SECRET_KEY` invalidates sessions and pending invite/reset links; a
  different `SERVICE_TOKEN_PEPPER` invalidates Bud result-sync credentials; a
  different `INTEGRATION_ENCRYPTION_KEY` makes configured GitHub/GitLab secrets
  unreadable until they are rotated.

## Supply chain

Every release build publishes an SPDX SBOM as a CI artifact
(`bloom-sbom.spdx.json`) alongside the container image, and CI runs Bandit,
`pip-audit`, and blocking `npm audit` checks on every push.

Backend dependencies, the CI tools and supervisor are pinned with their
hashes in [`uv.lock`](../uv.lock). CI and the image build install from it with
hash checks and without building any source distribution
(`uv sync --frozen --no-build`, and `uv pip install --require-hashes --no-build`
from `uv export` in the image), so builds are reproducible. CI and the image
build check that the lock matches `pyproject.toml` with
`uv lock --check --no-build`. Dependabot watches uv, npm, Docker and GitHub
Actions weekly. Refresh the pins with:

```bash
uv lock --upgrade --no-build
```

The container starts as root only to prepare its runtime directories, the
ownership of its data and of its standard output and error streams and, on
Cloudron, the persistent secrets and the database migrations. It then runs
everything as `appuser`: supervisord, nginx on port 8080 (master and
workers), and uvicorn. Kubernetes `runAsNonRoot` policies are not supported,
as the start needs root.
