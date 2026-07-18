# Bloom

Bloom is a self-hosted product lifecycle management application for requirements, controlled documents, verification assets, test planning, and end-to-end traceability.

## Run the published product image

- Container image: [`ghcr.io/mbedlabs/bloom`](https://github.com/orgs/MbedLabs/packages/container/package/bloom)
- GitHub Packages page: [MbedLabs/bloom](https://github.com/orgs/MbedLabs/packages/container/package/bloom)
- Supported platforms: `linux/amd64` and `linux/arm64`
- Application port: container `8080` (the provided Compose file publishes it on host port `8000`)
- Process-liveness endpoint: `GET /api/health`

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
openssl rand -hex 24  # use for the one-time ADMIN_PASSWORD
```

Edit `.env` before starting. At minimum:

- replace `POSTGRES_PASSWORD`, `SECRET_KEY`, and `ADMIN_PASSWORD` with the generated values;
- replace `ADMIN_EMAIL` with a real address (production rejects `admin@example.com`);
- set `APP_BASE_URL`, `FRONTEND_BASE_URL`, and `BLOOM_APP_URL` to the public HTTPS Bloom URL;
- set `BUD_APP_URL` to the public Bud URL if the products are connected; and
- leave `RUN_STARTUP_DATA_REPAIR=false` for a new production database.

The required credential fields are intentionally empty. Compose enforces `POSTGRES_PASSWORD`, `SECRET_KEY`, `ADMIN_EMAIL`, and `ADMIN_PASSWORD` during configuration interpolation, so an unedited copy fails before any container starts.

`SECRET_KEY` must be at least 32 characters and must be backed up in your secret store. Losing or changing it invalidates sessions, integration tokens, and pending invitation/reset links.

### 2. Pull and start Bloom

```bash
docker compose pull
docker compose up -d
docker compose logs -f bloom
```

The Compose service waits for PostgreSQL, runs `alembic upgrade head`, and then starts Bloom. Check process liveness from the host:

```bash
curl --fail http://localhost:8000/api/health
```

`/api/health` confirms that the Bloom web process is responding; it does not query PostgreSQL. For readiness or availability monitoring, combine it with PostgreSQL health and, where appropriate, a synthetic authenticated request that exercises a database-backed Bloom operation.

Open <http://localhost:8000> (or your configured HTTPS URL) and sign in with `ADMIN_EMAIL` and the one-time `ADMIN_PASSWORD` from `.env`.

### 3. Finish the one-time administrator bootstrap

`AUTO_SEED_ADMIN=true` creates the first administrator only when no account with `ADMIN_EMAIL` exists. Rotate the bootstrap password immediately through the authenticated API:

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

Then set `AUTO_SEED_ADMIN=false` in `.env`, replace the now-unused `ADMIN_PASSWORD` value with a different random value, and recreate the service:

```bash
docker compose up -d --force-recreate bloom
```

Keep the administrator credential and `SECRET_KEY` in a secret manager, not in source control.

## Public URLs, TLS, and email

Put Bloom behind a TLS-terminating reverse proxy for an internet-facing deployment and proxy to host port `8000`. The public URL settings are used in browser links and email workflows:

- `APP_BASE_URL`, `FRONTEND_BASE_URL`, and `BLOOM_APP_URL`: the externally reachable Bloom origin;
- `BUD_APP_URL`: the externally reachable Bud origin used by Bloom's Bud navigation and cross-links;
- `TESTSTATION_APP_URL`: retained compatibility URL for the execution application; normally the same origin as Bud.

SMTP is disabled in the example configuration. Before inviting users or relying on email verification and password resets, configure `SMTP_HOST`, credentials, sender/reply-to addresses, TLS mode, and then set `SMTP_ENABLED=true`. Restart Bloom after changing runtime settings.

## Use Bloom

After signing in:

1. Create a project and choose its three-character prefix. Bloom uses the prefix in stable public IDs such as `VCU-REQ-001` and `VCU-TC-001`.
2. Add project members and choose the artefact types external users may see.
3. Capture requirements and controlled documents, then link designs, risks, changes, test concepts, and verification assets.
4. Build test cases, suites, and campaigns; use traceability and coverage views to find gaps.
5. Create baselines when a controlled project state needs to be preserved.
6. Configure a project's GitHub or GitLab integration if defects should link to an external issue tracker.

## Connect Bloom and Bud

Bloom issues the token that Bud uses to post execution results:

1. Sign in to Bloom as an administrator.
2. Open **Settings → PLM Integration Token Management**.
3. Select **Generate New Token** and copy the token immediately. Generating another token invalidates the previous integration token for that administrator.
4. Sign in to Bud as an administrator and open **Settings → PLM Integration (Bloom)**.
5. Enter the Bloom base URL and paste the generated token, then save.
6. Set Bloom's `BUD_APP_URL` to Bud's public origin so navigation and cross-links open the correct instance.

The integration is intentionally limited to **test-case execution**. Bud sends results keyed by Bloom `tc_id`; Bloom updates matching test cases and their campaign line items. Bud does not create or synchronize Bloom campaigns, suites, requirements, or documents.

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
curl --fail http://localhost:8000/api/health
```

Compose runs Alembic migrations before the upgraded application starts. Database migrations may not be backward compatible: restore the pre-upgrade database backup before starting an older image. Never run an older application against a schema migrated by a newer release unless that release explicitly documents support.

## Observe and troubleshoot Bloom

- `docker compose ps` shows container and health status.
- `docker compose logs -f bloom` streams application, nginx, and migration output.
- `GET /api/health` checks process liveness only; it does not prove PostgreSQL availability.
- `GET /api/metrics` exposes Prometheus metrics when `ENABLE_METRICS=true`.
- `LOG_JSON=true` emits structured production logs; use `X-Request-ID` to correlate requests.
- If startup stops before the server begins, inspect the Bloom logs for configuration validation or Alembic errors.
- If sign-in fails on first boot, confirm the production admin email is not `admin@example.com`, the password is at least 16 characters, and `AUTO_SEED_ADMIN` was enabled for that first start.
- If Bud results do not appear, verify the Bloom URL and token in Bud, confirm the token belongs to an active Bloom admin, and confirm Bud results contain matching `tc_id` metadata.

The full monitoring, backup/restore, upgrade, and disaster-recovery reference is in [docs/OPERATIONS.md](docs/OPERATIONS.md).

## Contribute and develop locally

Operator setup above uses the published package. Contributors can build and test the combined FastAPI/React source tree locally.

### Install the same dependencies as CI

Use Python 3.11 and Node.js 20:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]" -c constraints.txt
pip install black==25.1.0 isort==5.13.2 bandit==1.8.3 pip-audit
npm --prefix ui ci
```

### Run the same checks as CI

Start the CI PostgreSQL service:

```bash
docker run --rm -d --name bloom-ci-postgres \
  -e POSTGRES_USER=test_user \
  -e POSTGRES_PASSWORD=test_password \
  -e POSTGRES_DB=test_bloom \
  -p 5432:5432 \
  postgres:16
```

Then run the backend validation, schema setup, migrations, tests, and UI checks:

```bash
black --check --diff app/ tests/
isort --profile black --check-only --diff app/ tests/
bandit -r app/ -ll
pip-audit || true

export DATABASE_URL=postgresql+asyncpg://test_user:test_password@localhost:5432/test_bloom
export SECRET_KEY=test-secret-key-for-ci-at-least-32-characters-long
export BLOOM_DOTENV_DISABLED=1
export BLOOM_DISABLE_RATE_LIMIT=1

python -c "
import asyncio
from app.core.database import create_tables
asyncio.run(create_tables())
print('Base tables created from models.')
"
pip install alembic
alembic upgrade head

export ENABLE_DOCS=false
pytest --cov=app --cov-report=xml --cov-report=term-missing --cov-fail-under=55 tests/ -v

npm --prefix ui run lint
npx --prefix ui tsc --project ui/tsconfig.json --noEmit
npm --prefix ui run test -- --coverage
```

Stop the temporary database when finished:

```bash
docker stop bloom-ci-postgres
```

Run development servers separately if you need hot reload:

```bash
uvicorn app.main:app --reload --port 8000
npm --prefix ui run dev
```

Build the combined product image with:

```bash
docker build -t bloom:local .
```

## Project resources

- [Operating Bloom](docs/OPERATIONS.md)
- [Changelog](CHANGELOG.md)
- [Contributing guide](CONTRIBUTING.md)
- [Contributor License Agreement](CLA.md)
- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Security policy](SECURITY.md)
- [GNU Affero General Public License v3.0](LICENSE)

## License

Bloom is licensed under the [GNU Affero General Public License v3.0](LICENSE). Deploying a modified network service requires offering its corresponding source to users as required by the AGPL.
