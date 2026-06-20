# Bloom

Bloom is the combined product repo for the EmbedLabs product lifecycle management app. It keeps the FastAPI backend at the repo root, the React frontend under [`frontend/`](frontend), and ships a single product image that serves both the UI and the `/api` surface.

## What is in this repo

- Backend API and Alembic migrations at the root
- Frontend application in [`frontend/`](frontend)
- One combined Docker image build from the root `Dockerfile`
- One product CI workflow in [`.github/workflows/ci-cd.yml`](.github/workflows/ci-cd.yml)

## Version

This combined product repo is currently at `1.0.0`.

## Quick start

```bash
cp .env.example .env
docker compose up -d postgres
docker compose run --rm bloom alembic upgrade head
docker compose up -d bloom
curl -sf http://localhost:8000/api/health
```

Open `http://localhost:8000`.

For the first admin bootstrap, temporarily set `AUTO_SEED_ADMIN=true` in `.env`, start Bloom once, sign in, then set it back to `false`.

## Local development

Backend:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm ci
npm run dev
```

## Verification

Backend checks:

```bash
black --check --diff app/ tests/
isort --profile black --check-only --diff app/ tests/
pytest --cov=app --cov-report=term-missing --cov-fail-under=50 tests/ -v
```

Frontend checks:

```bash
cd frontend
npm run lint
npx tsc --noEmit
npm run test -- --coverage
```

Combined image:

```bash
docker build -t bloom:1.0.0 .
docker run --rm -p 8000:8080 bloom:1.0.0
```

## IAM and invitation model

- Admins invite users and maintainers through the app.
- External users are read-only and should only see permitted project data.
- Bud integrations should point `BUD_APP_URL` at the Bud product repo deployment, `http://localhost:8001` by default in local combined-repo development.

## Production notes

- `BLOOM_ENV=production` rejects unsafe bootstrap defaults.
- `RUN_STARTUP_DATA_REPAIR` defaults off in production.
- `AUTO_SEED_ADMIN` defaults off in production and should only be enabled for controlled bootstrap or rotation windows.

## License

This project is licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0)**. See [LICENSE](LICENSE).
