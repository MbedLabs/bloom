# Bloom by EmbedLabs

Bloom by EmbedLabs is a self-hosted product lifecycle management application for requirements, controlled documents, verification assets, test planning, and end-to-end traceability.

Bloom is available under the **GNU Affero General Public License v3.0 only (AGPL-3.0-only)**. EmbedLabs also offers commercial licensing for use cases that cannot comply with the AGPL, plus paid **priority support** and **custom feature development**. Contact `dev@embedlabs.net`.

## Run the published product image

- Container image: [`ghcr.io/mbedlabs/bloom`](https://github.com/orgs/MbedLabs/packages/container/package/bloom)
- GitHub Packages page: [MbedLabs/bloom](https://github.com/orgs/MbedLabs/packages/container/package/bloom)
- Supported platforms: `linux/amd64` and `linux/arm64`
- Application port: container `8080` (the provided Compose file publishes it on host port `8000`)
- Liveness endpoint: `GET /api/health` (process only); readiness endpoint: `GET /api/ready` (`SELECT 1`, used by the container healthcheck)

Release tags publish immutable versioned images. For example, `v1.0.0-rc.1` publishes `v1.0.0-rc.1` and `1.0.0-rc.1`; `v1.0.0` publishes `v1.0.0`, `1.0.0`, `1.0`, `1`, and `latest`. Every release also has a `sha-...` tag. Pre-releases never move `latest` or the major/minor tags; a stable version with only `+build` metadata still does.

## What Bloom gives your team

Bloom keeps lifecycle work in one project workspace so teams can:

- manage requirements, shared documents, test cases, suites, campaigns, test concepts, risks, changes, defects, and baselines;
- connect artefacts and inspect coverage through traceability views;
- import, export, search, and report on controlled project data;
- assign stable, human-readable project IDs to records;
- give maintainers and external users scoped project access and customer-visible artefacts;
- connect GitHub or GitLab defect tracking to a project; and
- receive test-case execution status from [Bud](https://github.com/MbedLabs/bud).

## Quick start with Docker Compose

You need Docker Engine with Docker Compose v2. The reference deployment runs Bloom and PostgreSQL, keeps PostgreSQL private to the Compose network, and stores database data in a named volume.

### 1. Create your production configuration

```bash
cp .env.example .env
openssl rand -hex 32  # use for POSTGRES_PASSWORD
openssl rand -hex 32  # use for SECRET_KEY
openssl rand -hex 32  # use for SERVICE_TOKEN_PEPPER
openssl rand -hex 24  # use for the one-time ADMIN_PASSWORD
```

Edit `.env` before starting. At minimum:

- replace `POSTGRES_PASSWORD`, `SECRET_KEY`, `SERVICE_TOKEN_PEPPER`, and `ADMIN_PASSWORD` with independent generated values;
- replace `ADMIN_EMAIL` with a real address (production rejects `admin@example.com`);
- set `APP_BASE_URL`, `FRONTEND_BASE_URL`, and `BLOOM_APP_URL` to the public HTTPS Bloom URL;
- set `BUD_APP_URL` to the public Bud URL if the products are connected; and
- leave `RUN_STARTUP_DATA_REPAIR=false` for a new production database; and
- keep the shipped `AUTO_SEED_ADMIN=false` setting. For a new instance with an empty database, explicitly change it to `true` immediately before the one-time first-administrator startup.

The required credential fields are intentionally empty. Compose enforces `POSTGRES_PASSWORD`, `SECRET_KEY`, `ADMIN_EMAIL`, and `ADMIN_PASSWORD` during configuration interpolation, so an unedited copy fails before any container starts.

`SECRET_KEY` and `SERVICE_TOKEN_PEPPER` must each be at least 32 characters and must be backed up in your secret store. Losing `SECRET_KEY` invalidates sessions and pending invitation/reset links; losing `SERVICE_TOKEN_PEPPER` invalidates Bud result-sync credentials.

### 2. Pull and start Bloom

For the initial startup of a new instance only, opt in to administrator creation by setting `AUTO_SEED_ADMIN=true` in `.env`. Do not enable it for an existing instance.

```bash
docker compose pull
docker compose up -d
docker compose logs -f bloom
```

The Compose service waits for PostgreSQL, runs `alembic upgrade head`, and then starts Bloom. Check readiness from the host:

```bash
curl --fail http://localhost:8000/api/ready
```

`/api/ready` runs `SELECT 1` and returns `{"status":"ready","database":"connected"}` only once Bloom can reach PostgreSQL (`503` otherwise). `/api/health` is the cheaper liveness probe: it confirms the web process is responding but deliberately does not query PostgreSQL.

Open <http://localhost:8000> (or your configured HTTPS URL) and sign in with `ADMIN_EMAIL` and the one-time `ADMIN_PASSWORD` from `.env`.

### 3. Finish the one-time administrator bootstrap

If you opted in for the first startup, `AUTO_SEED_ADMIN=true` creates the first administrator only when no account with `ADMIN_EMAIL` exists. Rotate the bootstrap password immediately through the authenticated API:

```bash
export BLOOM_URL=http://localhost:8000
export ADMIN_EMAIL='admin@your-domain.example'
read -r -s -p 'Bootstrap password: ' BOOTSTRAP_PASSWORD; echo
read -r -s -p 'New administrator password: ' NEW_ADMIN_PASSWORD; echo

ACCESS_TOKEN=$(curl --fail --silent --show-error \
  --header 'Content-Type: application/json' \
  --data "$(ADMIN_EMAIL="$ADMIN_EMAIL" BOOTSTRAP_PASSWORD="$BOOTSTRAP_PASSWORD" python3 -c 'import json, os; print(json.dumps({"email": os.environ["ADMIN_EMAIL"], "password": os.environ["BOOTSTRAP_PASSWORD"]}))')" \
  "${BLOOM_URL}/api/auth/login" \
  | python3 -c 'import json, sys; print(json.load(sys.stdin)["access_token"])')

curl --fail --silent --show-error \
  --request PUT \
  --header "Authorization: Bearer ${ACCESS_TOKEN}" \
  --header 'Content-Type: application/json' \
  --data "$(BOOTSTRAP_PASSWORD="$BOOTSTRAP_PASSWORD" NEW_ADMIN_PASSWORD="$NEW_ADMIN_PASSWORD" python3 -c 'import json, os; print(json.dumps({"current_password": os.environ["BOOTSTRAP_PASSWORD"], "new_password": os.environ["NEW_ADMIN_PASSWORD"]}))')" \
  "${BLOOM_URL}/api/auth/me/password"

unset BOOTSTRAP_PASSWORD NEW_ADMIN_PASSWORD ACCESS_TOKEN
```

Then immediately restore `AUTO_SEED_ADMIN=false` in `.env`, replace the now-unused `ADMIN_PASSWORD` value with a different random value, and recreate the service:

```bash
docker compose up -d --force-recreate bloom
```

Keep the administrator credential and `SECRET_KEY` in a secret manager, not in source control.

## Public URLs, TLS, and email

Put Bloom behind a TLS-terminating reverse proxy for an internet-facing deployment and proxy to host port `8000`. The public URL settings are used in browser links and email workflows:

The email sender display name is fixed to `Bloom PLM by EmbedLabs` and is not configurable. Configure the SMTP sender address, server credentials, and optional reply-to address in `.env`.

- `APP_BASE_URL`, `FRONTEND_BASE_URL`, and `BLOOM_APP_URL`: the externally reachable Bloom origin;
- `BUD_APP_URL`: optional externally reachable Bud origin; setting it enables Bloom's Bud navigation and execution cross-links;
- `TESTSTATION_APP_URL`: optional compatibility alias for the Bud origin.

SMTP is disabled in the example configuration. Before inviting users or relying on email verification and password resets, configure `SMTP_HOST`, credentials, sender/reply-to addresses, TLS mode, and then set `SMTP_ENABLED=true`. Restart Bloom after changing runtime settings.

## Use Bloom

After signing in:

1. Create a project and choose its three-character prefix. Bloom uses the prefix in stable public IDs such as `VCU-REQ-001` and `VCU-TC-001`.
2. Add project members and choose the artefact types external users may see.
3. Capture requirements and controlled documents, then link designs, risks, changes, test concepts, and verification assets.
4. Build test cases, suites, and campaigns; use traceability and coverage views to find gaps.
5. Create baselines when a controlled project state needs to be preserved.
6. Configure a project's GitHub or GitLab integration if defects should link to an external issue tracker.

### ReqIF imports

Bloom accepts ZIP archives containing **exactly one `.reqif` member**. The request and uncompressed ReqIF member are each limited to **25 MiB**. Archives are limited to **100 entries** and a **20:1 compression ratio**. A single import is limited to 999 specification objects, 10,000 relations, and 100 hierarchy levels. Bloom enforces the request cap while streaming, runs parsing in a time-limited worker process, permits five attempts per user per 15 minutes, and permits one active import per project.

These controls validate structure and resource use; they are not a malware scan. Do not advertise ReqIF imports as “security scanned” unless the deployment also connects an appropriate ClamAV or YARA scanning stage.

## Connect Bloom and Bud

Bloom and Bud are independently deployable. `bud-runner` and `budtestlibrary` communicate only with Bud and never call or require Bloom. If both applications are deployed, Bloom can issue the narrowly scoped credential that Bud uses to post test-case execution results:

1. Sign in to Bloom as an administrator.
2. Open **Settings → Bud Result-Sync Credentials**.
3. Create a credential and copy the `blm_sync_` token immediately; Bloom stores only its keyed hash and will not display it again.
4. Sign in to Bud as an administrator and open **Settings → PLM Integration (Bloom)**.
5. Enter the Bloom base URL and paste the scoped credential, then save. Bud encrypts it at rest and never returns it through settings APIs.
6. Set Bloom's `BUD_APP_URL` to Bud's public origin so navigation and cross-links open the correct instance.

The credential expires after 90 days, can be rotated or revoked independently, and has only the `test-results:write` scope. It cannot call user, project, or administration APIs.

The integration is intentionally limited to **test-case execution results**. Bud sends outcomes keyed by Bloom `tc_id`; Bloom updates the matching test case and any line items in campaigns that already contain it. The endpoint lives under the campaigns router for historical API compatibility, but Bud does not create or synchronize campaigns, suites, requirements, or documents.

## Run without Compose

The image does not include PostgreSQL. With an existing PostgreSQL database reachable from Docker, run migrations once and then start the application:

```bash
export BLOOM_IMAGE=ghcr.io/mbedlabs/bloom:1.0.0
export DATABASE_URL='postgresql+asyncpg://bloom:password@database.example:5432/bloom'

docker pull "$BLOOM_IMAGE"
docker run --rm \
  --env-file .env \
  --env DATABASE_URL="$DATABASE_URL" \
  "$BLOOM_IMAGE" \
  alembic upgrade head

docker run -d \
  --name bloom \
  --restart unless-stopped \
  --publish 8000:8080 \
  --env-file .env \
  --env DATABASE_URL="$DATABASE_URL" \
  "$BLOOM_IMAGE"
```

Use a URL-encoded database password in `DATABASE_URL` when it contains reserved URL characters.

## Persistence and backups

Bloom's durable state lives in PostgreSQL. The Compose deployment stores it in `bloom-postgres-data`; removing the application container does not remove that volume. Do not use `docker compose down -v` unless you intend to delete the database.

Create a PostgreSQL custom-format backup:

```bash
docker compose exec -T postgres sh -c \
  'pg_dump --format=custom --username="$POSTGRES_USER" --dbname="$POSTGRES_DB"' \
  > "bloom-$(date +%F).dump"
```

Copy backups off the Docker host and test restores on a separate database. Preserve `.env` secrets—especially `SECRET_KEY`—with the database backup. See [Operating Bloom](docs/OPERATIONS.md) for restore and disaster-recovery guidance.

## Upgrade or roll back

Pin `BLOOM_VERSION` in `.env` to the exact release you operate; use a full version such as `1.0.0` or a pre-release such as `1.0.0-rc.1`. `latest` follows stable releases only.

```bash
# Back up first, then edit BLOOM_VERSION in .env.
docker compose pull bloom
docker compose up -d bloom
curl --fail http://localhost:8000/api/ready
```

Compose runs Alembic migrations before the upgraded application starts. Database migrations may not be backward compatible: restore the pre-upgrade database backup before starting an older image. Never run an older application against a schema migrated by a newer release unless that release explicitly documents support.

## Observe and troubleshoot Bloom

- `docker compose ps` shows container and health status.
- `docker compose logs -f bloom` streams application, nginx, and migration output.
- `GET /api/health` checks process liveness only; it does not prove PostgreSQL availability. `GET /api/ready` runs `SELECT 1` and returns `503` when the database is unreachable.
- `GET /api/metrics` exposes Prometheus metrics when `ENABLE_METRICS=true`.
- `LOG_JSON=true` emits structured production logs; use `X-Request-ID` to correlate requests.
- If startup stops before the server begins, inspect the Bloom logs for configuration validation or Alembic errors.
- If sign-in fails on first boot, confirm the production admin email is not `admin@example.com`, the password is at least 16 characters, and `AUTO_SEED_ADMIN` was enabled for that first start.
- If Bud results do not appear, verify the Bloom URL and configured `blm_sync_` credential in Bud, rotate it if it expired or was revoked, and confirm Bud results contain matching `tc_id` metadata.

The full monitoring, backup/restore, upgrade, and disaster-recovery reference is in [docs/OPERATIONS.md](docs/OPERATIONS.md).

## Contributing

Bloom users and operators should deploy the published image described above. Source development instructions belong in the [contributing guide](CONTRIBUTING.md); the authoritative automated checks are in [`.github/workflows/ci-cd.yml`](.github/workflows/ci-cd.yml). Contributions require acceptance of the [Contributor License Agreement](CLA.md).

## Project resources

- [Operating Bloom](docs/OPERATIONS.md)
- [Changelog](CHANGELOG.md)
- [Contributing guide](CONTRIBUTING.md)
- [Contributor License Agreement](CLA.md)
- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Security policy](SECURITY.md)
- [GNU Affero General Public License v3.0 only](LICENSE)

## Security and support

Report vulnerabilities according to the [security policy](SECURITY.md). Community bug reports and feature proposals belong in GitHub Issues. EmbedLabs also offers paid **priority support** and **custom feature development** for teams that need response commitments, integration work, deployment assistance, or product extensions; contact `dev@embedlabs.net`.

## License

Bloom by EmbedLabs is licensed under the [GNU Affero General Public License v3.0 only (AGPL-3.0-only)](LICENSE). Commercial licenses are available from EmbedLabs for use cases that cannot comply with the AGPL. Deploying a modified network service under the AGPL requires offering its corresponding source to users; contact `dev@embedlabs.net` for commercial licensing.
