# Bloom

Bloom is an open source product lifecycle management platform for teams that need requirements, documents, verification assets, and traceability in one place.

## What you can do with Bloom

- Manage requirements, shared documents, test cases, suites, campaigns, and baselines from one workspace
- Track traceability and coverage across specification and verification assets
- Organize project data with stable human-readable IDs and change history
- Share controlled project views with internal teams and external stakeholders
- Connect lifecycle records with Bud execution workflows

## Self-host Bloom

Bloom ships as a combined product repo with a FastAPI backend at the repository top level, a React UI in [`ui/`](ui), and one product image that serves both the UI and the `/api` surface.

Bloom requires PostgreSQL plus runtime configuration for database access, application secrets, public URLs, admin access, and email delivery. Run `alembic upgrade head` before serving traffic.

## Get Started

- Review [`docker-compose.yml`](docker-compose.yml) for a reference self-host layout
- Use [`Dockerfile`](Dockerfile) if you want to build the combined product image directly
- Verify the deployed instance through the `/api/health` endpoint on your Bloom URL

## Local Development

Backend:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

UI:

```bash
cd ui
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

UI checks:

```bash
cd ui
npm run lint
npx tsc --noEmit
npm run test -- --coverage
```

Combined image:

```bash
docker build -t bloom:1.0.0 .
```

## Resources

- [`CHANGELOG.md`](CHANGELOG.md)
- [`CONTRIBUTING.md`](CONTRIBUTING.md)

## License

This project is licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0)**. See [LICENSE](LICENSE).
