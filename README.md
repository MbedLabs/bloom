# Bloom PLM by EmbedLabs

Bloom PLM by EmbedLabs is a source-available product lifecycle management application for requirements, controlled documents, verification assets, test planning, risks, changes, defects, baselines, and end-to-end traceability.

> **Release status:** 1.0.0 public beta. See the [changelog](CHANGELOG.md) for what this release includes.

## Licence status

Bloom is distributed under the [EmbedLabs Source Available License 1.0](LICENSE). It is **source-available**, not Open Source under the Open Source Definition.

The licence permits personal, educational, evaluation, research, and internal business use, including modification for those permitted uses. A separate professional licence is required for resale, third-party hosting, managed services, commercial redistribution, white-labelling, or embedding Bloom in a third-party commercial offering.

The required `Powered by EmbedLabs` attribution must remain visible as described in the licence. Product names and logos are not licensed for modified forks.

The separate `bud-runner` and `budtestlibrary` Python packages remain independent AGPL-3.0-only open-source projects. Their licences do not change Bloom's application licence.

For professional licensing, deployment, integration, priority support, or custom development, contact `sales@embedlabs.de`.

## Container image

- **Image:** `ghcr.io/mbedlabs/bloom`
- **Package:** [Bloom on GitHub Packages](https://github.com/orgs/MbedLabs/packages/container/package/bloom)
- **Platforms:** `linux/amd64` and `linux/arm64`
- **Container port:** `8080`
- **Reference host port:** `8000`

The published image contains the Bloom web application and API. You do not need to build the frontend or install Python dependencies to host it.

## What Bloom provides

- Requirements and controlled-document management
- Test cases, suites, campaigns, and test concepts
- Risks, changes, defects, and baselines
- Traceability links and coverage views
- Stable human-readable project identifiers
- Scoped project access for maintainers and external users
- GitHub and GitLab defect integrations
- Optional execution-result synchronisation from Bud
- ReqIF import and export workflows

Bloom works independently. Bud integration is optional and limited to test-case execution outcomes.

## Quick start

### Prerequisites

- Docker Engine with Docker Compose v2
- Git
- `openssl`
- Available host port `8000`

### 1. Get the deployment files

```bash
git clone https://github.com/MbedLabs/bloom.git
cd bloom
cp .env.example .env
```

### 2. Configure secrets

Generate independent values for PostgreSQL, application signing, scoped-service credentials, and the initial administrator password:

```bash
openssl rand -hex 32
openssl rand -hex 32
openssl rand -hex 32
openssl rand -hex 24
```

`INTEGRATION_ENCRYPTION_KEY` must be a Fernet key (not a hex string) — it encrypts external tracker credentials and webhook secrets at rest:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Replace every active placeholder in `.env`. At minimum configure:

- `POSTGRES_PASSWORD`
- `SECRET_KEY`
- `SERVICE_TOKEN_PEPPER`
- `INTEGRATION_ENCRYPTION_KEY`
- `ADMIN_EMAIL`
- `ADMIN_PASSWORD` (at least 16 characters in production)
- `ADMIN_FULL_NAME`
- `APP_BASE_URL`
- `FRONTEND_BASE_URL`
- `BLOOM_APP_URL`

Set `BUD_APP_URL` only when Bud navigation and result links are required.

In production (`BLOOM_ENV=production`) Bloom fails closed at startup: `SECRET_KEY` must be a strong non-placeholder value of at least 32 characters, `ADMIN_PASSWORD` must be changed from the default and at least 16 characters, and `INTEGRATION_ENCRYPTION_KEY` must be a valid Fernet key so integration credentials are always encrypted at rest. The reference Compose file additionally refuses to start unless `POSTGRES_PASSWORD`, `SECRET_KEY`, `ADMIN_EMAIL`, and `ADMIN_PASSWORD` are set.

Keep `RUN_STARTUP_DATA_REPAIR=false` in production. Set `AUTO_SEED_ADMIN=true` only for the one-time first-administrator bootstrap on a new empty database, then restore it to `false` immediately.

### 3. Pull, migrate, and start

Pin the image by setting `BLOOM_VERSION` in `.env` (for example `BLOOM_VERSION=1.0.0`; the default is `stable`). The reference Compose deployment waits for PostgreSQL, runs Alembic migrations (`alembic upgrade head`) before the app serves traffic, and starts Bloom:

```bash
docker compose pull
docker compose up -d
```

Check the migration and startup logs:

```bash
docker compose logs -f bloom
```

### 4. Verify

```bash
docker compose ps
curl -fsS http://localhost:8000/api/ready
```

`/api/health` is process liveness. `/api/ready` verifies PostgreSQL connectivity.

## ReqIF imports

Bloom validates bounded ReqIF imports before processing. Current protections include request-size, archive-entry, uncompressed-size, compression-ratio, object-count, relation-count, hierarchy-depth, timeout, rate, and per-project concurrency limits.

These controls validate structure and resource consumption. They are not a malware scan.

## Connect Bloom and Bud

Bloom and Bud are independently deployable. When both are used:

1. Create a narrowly scoped Bud result-sync credential in Bloom.
2. Configure the Bloom URL and credential in Bud.
3. Set Bloom's `BUD_APP_URL` when navigation and execution links should open Bud.

The integration accepts test-case execution outcomes keyed by Bloom `tc_id`. It does not make Bloom dependent on Bud and does not synchronise complete campaigns, requirements, or documents.

## Persistence and backups

Bloom's durable application state is stored in PostgreSQL through the `bloom-postgres-data` volume. Back up the database and deployment secrets together, and test restoration on a separate instance.

See [`docs/OPERATIONS.md`](docs/OPERATIONS.md) for backup, restore, upgrade, and disaster-recovery procedures.

## Image tags

Set `BLOOM_VERSION` in `.env` to the tag `docker compose` should pull.

| Container tag | Meaning |
|---|---|
| `1.0.0` | Exact production version — pin this for production |
| `1.0` / `1` | Moving stable channels tracking the newest `1.0.x` / `1.x` |
| `stable` | Newest stable semantic-version release |
| `latest` | Rolling image from `main`; not guaranteed to be a stable release |
| `dev` | Rolling image from the `dev` branch |
| `sha-<commit>` | Immutable image for exact source/image traceability |

Every moving tag (`stable`, `latest`, `1.0`, `1`, a branch name) is promoted to an image only after that exact image passes the published-image end-to-end tests, so a tag never resolves to an untested build. Pin a full semantic version (`BLOOM_VERSION=1.0.0`) for production.

## Upgrading

1. Read the [changelog](CHANGELOG.md) for the target release, and back up the `bloom-postgres-data` volume and your deployment secrets first (see [Persistence and backups](#persistence-and-backups)).
2. Set the new version in `.env`, for example `BLOOM_VERSION=1.0.0`.
3. Pull and restart. The Bloom container runs `alembic upgrade head` before it serves traffic:

```bash
docker compose pull
docker compose up -d
```

4. Confirm the running image and database:

```bash
curl -fsS http://localhost:8000/api/version
curl -fsS http://localhost:8000/api/ready
```

To roll back, restore the pre-upgrade database backup and set `BLOOM_VERSION` to the previous release. Downgrades that require reversing a migration are not supported — restore from backup instead.

## Security and documentation

- [Operating Bloom](docs/OPERATIONS.md)
- [Security policy](SECURITY.md)
- [Changelog](CHANGELOG.md)
- [Contributing guide](CONTRIBUTING.md)
- [Contributor License Agreement](CLA.md)
- [EmbedLabs Source Available License](LICENSE)

API documentation is disabled by default. Enable it only in a trusted development environment.

## Contributing

Contributions require explicit acceptance of [`CLA.md`](CLA.md) through the pull-request declaration. See [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Professional services

Professional licensing, deployment assistance, integrations, priority support, and custom engineering are available through [EmbedLabs Professional Services](https://embedlabs.de).
