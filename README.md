# Bloom PLM by EmbedLabs

Bloom PLM is a self-hosted product lifecycle management platform for requirements, controlled documents, verification, risks, changes, defects, baselines, and end-to-end traceability.

> **Release:** 1.0.0 public beta

## What Bloom provides

- Requirements and controlled documents across supported artefact types
- Test cases, suites, campaigns, concepts, and verification planning
- Risks, changes, defects, parameters, and baselines
- Traceability links, relationship views, and coverage analysis
- Stable human-readable identifiers for controlled project records
- Administrator, maintainer, and external-user access controls
- ReqIF import plus CSV and PDF exports
- GitHub, GitLab, and Jira synchronization for defects and change requests
- Optional test-case execution outcomes from Bud TMP
- Readiness, health, metrics, structured logging, and backup workflows

## How Bloom fits with Bud

Bloom manages product definition, traceability, and verification intent. Bud manages test execution evidence. Each product runs independently.

When connected, the execution path is:

1. Tests use [`budtestlibrary`](https://github.com/MbedLabs/bud-test-library) for lifecycle, assertions, results, and optional Bloom test-case metadata.
2. [`bud-runner`](https://github.com/MbedLabs/bud-runner) executes those tests and uploads results to [Bud TMP](https://github.com/MbedLabs/bud).
3. Bud sends scoped execution outcomes to the matching Bloom test cases.

Bloom does not require Bud, `bud-runner`, or `budtestlibrary` for its PLM workflows.

## Quick start

### Requirements

- Docker Engine with Docker Compose v2
- `curl`
- `openssl`
- Available host port `8000`

### 1. Download the deployment files

```bash
mkdir bloom-deployment
cd bloom-deployment

curl -fsSLo compose.yaml \
  https://raw.githubusercontent.com/MbedLabs/bloom/main/docker-compose.yml
curl -fsSLo .env \
  https://raw.githubusercontent.com/MbedLabs/bloom/main/.env.example
```

This downloads only the deployment configuration. The application itself runs from `ghcr.io/mbedlabs/bloom`.

### 2. Configure Bloom

Generate independent secrets:

```bash
openssl rand -hex 32
openssl rand -hex 32
openssl rand -hex 24
```

Open `.env` and set at least:

- `POSTGRES_PASSWORD`
- `SECRET_KEY`
- `ADMIN_EMAIL`
- `ADMIN_PASSWORD`
- `ADMIN_FULL_NAME`
- `APP_BASE_URL`
- `FRONTEND_BASE_URL`
- `BLOOM_APP_URL`

For a new database, set `AUTO_SEED_ADMIN=true` for the first startup. In production, Bloom rejects a missing or weak signing key and requires an administrator password of at least 16 characters.

Keep `RUN_STARTUP_DATA_REPAIR=false`. The container applies database migrations with Alembic before starting the application.

Optional features use independent secrets:

- Set `SERVICE_TOKEN_PEPPER` to a random value of at least 32 characters when Bloom will issue scoped service credentials for Bud.
- Set `INTEGRATION_ENCRYPTION_KEY` to a Fernet key when GitHub, GitLab, or Jira synchronization will store credentials:

  ```bash
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  ```

Bloom starts without these optional secrets. Only the corresponding integration remains unavailable.

### 3. Pull and start

```bash
docker compose -f compose.yaml pull
docker compose -f compose.yaml up -d
```

Follow startup and migration logs:

```bash
docker compose -f compose.yaml logs -f bloom
```

After the first administrator has been created, set `AUTO_SEED_ADMIN=false` in `.env` and apply the configuration:

```bash
docker compose -f compose.yaml up -d bloom
```

### 4. Verify

```bash
docker compose -f compose.yaml ps
curl -fsS http://localhost:8000/api/ready
```

Open `http://localhost:8000`.

- `/api/health` checks process liveness.
- `/api/ready` checks application readiness and PostgreSQL connectivity.
- `/api/version` reports the running version.

## Connect Bloom to Bud

To receive test-case execution outcomes:

1. Set Bloom's `SERVICE_TOKEN_PEPPER` to an independent random value of at least 32 characters and restart Bloom.
2. In Bloom Settings, open **PLM Integration Token Management** and select **Create Credential**.
3. Copy the `blm_sync_…` credential when it is shown. Bloom displays it only once.
4. In Bud, configure `BUD_INTEGRATION_ENCRYPTION_KEY`.
5. Open **Settings → PLM Integration (Bloom)** in Bud and save Bloom's reachable URL and the scoped credential.
6. Set Bloom's `BUD_APP_URL` when Bloom navigation and execution links should open Bud.

The integration accepts test-case execution outcomes identified by Bloom `tc_id`. It does not synchronize complete campaigns, requirements, documents, or unrestricted Bloom data.

## Issue tracker synchronization

Defects and change requests can each track an issue in GitHub, GitLab, or Jira. Configure one integration per project per tracker under **Settings → Integrations**; credentials and webhook secrets are encrypted at rest with `INTEGRATION_ENCRYPTION_KEY`.

Inbound webhooks are rejected unless a webhook secret is configured and the delivery is authenticated, and each delivery identifier is accepted only once, so a captured request cannot be replayed.

| Tracker | Webhook endpoint | Authentication | Delivery identifier |
|---|---|---|---|
| GitHub | `/api/integrations/github/webhook` | `X-Hub-Signature-256` HMAC | `X-GitHub-Delivery` |
| GitLab | `/api/integrations/gitlab/webhook` | `X-Gitlab-Token` | `X-Gitlab-Event-UUID` |
| Jira | `/api/integrations/jira/webhook` | `X-Hub-Signature` HMAC | `X-Atlassian-Webhook-Identifier` |

Jira additionally needs the site base URL (for example `https://your-site.atlassian.net`) and the account e-mail owning the API token, because Jira Cloud authenticates with `email:api_token`. Jira status *names* are project-specific, so Bloom maps the issue's status **category**: `new` → Open, `indeterminate` → In Progress, `done` → Closed. Outbound status changes are applied as workflow transitions.

## ReqIF

Bloom validates ReqIF imports before processing them. Controls cover request size, archive entries, uncompressed member size, compression ratio, object and relation counts, hierarchy depth, processing time, request rate, and per-project concurrency.

These controls limit malformed or resource-intensive imports; they are not a malware scanner.

## Email

SMTP is optional for an installation that uses only the initial administrator. It is required for invitations, password resets, email verification, and approved email changes.

Set `SMTP_ENABLED=true` and configure the SMTP host, sender, authentication, and TLS values in `.env` before using those workflows.

## Data and backups

Bloom has two durable stores:

- `bloom-postgres-data` for PostgreSQL records
- `bloom-attachments` for document evidence under `/app/attachments`

`BLOOM_ATTACHMENT_DIR` identifies the attachment directory. The supplied
Compose file fixes it to `/app/attachments` and mounts `bloom-attachments`
there, so replacing or upgrading the application container does not erase
uploaded evidence. A non-Compose deployment must mount its own durable storage
at the configured path.

Interactive maintainer uploads default to ten starts per user in fifteen
minutes and one active upload per user. Configure those controls with
`BLOOM_ATTACHMENT_UPLOADS_PER_15_MINUTES` and
`BLOOM_MAX_CONCURRENT_ATTACHMENT_UPLOADS_PER_USER`. Scoped automated Bud report
publishing is separate from the human allowance. File, document, free-space,
and MIME controls are listed in `.env.example`.

Back up PostgreSQL, the attachment volume, and deployment secrets together, and test restoration on a separate installation.

Detailed backup, restore, upgrade, and recovery procedures are in [`docs/OPERATIONS.md`](docs/OPERATIONS.md).

## Images and versions

- **Image:** `ghcr.io/mbedlabs/bloom`
- **Package:** [Bloom on GitHub Packages](https://github.com/orgs/MbedLabs/packages/container/package/bloom)
- **Platforms:** `linux/amd64`, `linux/arm64`
- **Container port:** `8080`
- **Default host port:** `8000`

Set `BLOOM_VERSION` in `.env`:

| Tag | Use |
|---|---|
| `1.0.0` | Immutable production release |
| `1.0` / `1` | Moving release channels |
| `stable` | Newest stable release |
| `latest` | Rolling image from `main` |
| `dev` | Rolling image from `dev` |
| `sha-<commit>` | Exact source and image revision |

Pin a complete version such as `1.0.0` for production.

## Upgrade

1. Read [`CHANGELOG.md`](CHANGELOG.md).
2. Back up `bloom-postgres-data`, `bloom-attachments`, and `.env`.
3. Set the target `BLOOM_VERSION`.
4. Pull and restart:

   ```bash
   docker compose -f compose.yaml pull
   docker compose -f compose.yaml up -d
   ```

5. Verify `/api/version` and `/api/ready`.

Restore the pre-upgrade backup to roll back a release that changed the database schema. Database downgrades are not supported.

## Documentation

- [Operations](docs/OPERATIONS.md)
- [Security policy](SECURITY.md)
- [Changelog](CHANGELOG.md)
- [Contributing](CONTRIBUTING.md)
- [Contributor License Agreement](CLA.md)

API documentation is disabled by default. Enable it only in a trusted development environment.

## Branding

Do not remove, hide, obscure, replace, or render illegible the required **“Powered by EmbedLabs”** attribution.

Materially modified public forks or distributions must use a distinct product name, must not use the official product logo without written permission, and must not imply that they are official, supported, certified, or endorsed EmbedLabs releases.

See Sections 5 and 6 of the LICENSE for the binding terms.

## Licensing

Bloom PLM is distributed under the [EmbedLabs Source Available License 1.0](LICENSE).

The license permits personal, educational, evaluation, research, and internal business use, including modification for those uses. A separate professional license is required for resale, third-party hosting, managed services, commercial redistribution, white-labelling, or embedding Bloom in a third-party commercial product.

For professional licensing, deployment, integration, priority support, or custom development, contact `sales@embedlabs.de` or visit [EmbedLabs](https://www.embedlabs.net).
