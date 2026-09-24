# Operating Bloom

A practical guide for running Bloom in production: monitoring, logs, backup and
restore, upgrades, and disaster recovery. Runtime configuration lives in
environment variables — see [`.env.example`](../.env.example) for the full list.

## Image tags

Images are published to `ghcr.io/mbedlabs/bloom`:

| Tag | Moves? | Use for |
|---|---|---|
| `sha-<commit>` | immutable | exact reproducibility / debugging |
| `1.2.3` (full semver) | immutable | **production — pin this** |
| `1.2`, `1` | moving (stable releases) | tracking a minor/major line |
| `stable` | moving → newest stable release | low-maintenance production |
| `latest` | moving → newest `main` build | **development / staging only** |

Set `BLOOM_VERSION` in `.env` to a pinned version (e.g. `1.2.3`) or `stable`.
Never run `latest` in production — it is the rolling development build. `stable`
starts existing once you publish your first `vX.Y.Z` release tag.

## Health checks

- `GET /api/health` — **liveness**. Confirms the web process responds; it does not
  query PostgreSQL, so it never claims a database connection it has not verified.
- `GET /api/ready` — **readiness**. Runs `SELECT 1` against PostgreSQL and returns
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

- `GET /api/metrics` — Prometheus text format.
- `http_requests_total{method,path,status}` — request counts by route template.
- `http_request_duration_seconds{method,path}` — latency histogram.
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

## Jira defects

A Jira project can feed a Bloom project: a matching Jira issue creates a defect, and
the defect then follows the issue. The direction is Jira to Bloom unless the project
turns on two-way sync, which also pushes defect title and status changes to Jira.

In Bloom, as an administrator, open the project settings, choose Jira under External
issue tracker and fill in:

- Site URL (`https://your-site.atlassian.net`), account email and API token of the
  Atlassian account Bloom reads with.
- Webhook secret: any long random string; the same value goes into Jira.
- Jira project key, issue types (default `Bug`), and optionally a label, a custom field
  that holds Bloom test-case ids, and extra JQL used by the pull.
- The Jira priority to Bloom priority map.

In Jira, as a site administrator, open Settings, System, WebHooks and create a webhook:

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
- Updated, for a linked issue: title, description, priority and state follow Jira; a
  resolution closes the defect.
- Deleted: the defect stays and its issue state reads `Removed in Jira`.
- A delivery Jira retries with the same identifier is processed once.

Pull existing issues, on the same panel, searches Jira once with the saved filter and
creates the defects that do not exist yet (at most 1000 issues per pull). It only reads
from Jira.

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

- **RPO** equals your backup cadence — nightly dumps mean up to 24h of loss;
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

Backend dependencies are pinned in [`constraints.txt`](../constraints.txt)
(generated with `pip-compile`), and both the image build and CI install with
`-c constraints.txt`, so builds are reproducible. Dependabot watches pip, npm,
Docker and GitHub Actions weekly. Refresh the pins with:

```bash
pip install pip-tools
pip-compile --strip-extras --output-file=constraints.txt pyproject.toml
```

The container runs unprivileged end to end (`USER appuser` — supervisord,
nginx on port 8080, and uvicorn), which also satisfies Kubernetes
`runAsNonRoot` policies.
