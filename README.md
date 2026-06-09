# EmbedLabs Bloom - Product Lifecycle Management

Backend API for **Bloom**, EmbedLabs' Product Lifecycle Management. Bloom manages requirements, test cases, and traceability across the product lifecycle.

## Features

- **Project Management** - Organize requirements and test cases by project with auto-generated IDs (e.g. `PROJ-REQ-001`, `PROJ-TC-001`)
- **Requirement Hierarchy** - Parent/child requirement relationships with statuses (Draft → Review → Approved → Implemented → Verified)
- **Test Case Management** - Create test cases with structured steps and link them to requirements
- **Traceability Matrix** - Full coverage tracking (Covered / Partial / Uncovered) across requirements and test cases
- **Test Station Integration** - Link requirements to test runs in the [Bud Test Management Platform](https://github.com/MbedLabs/bud-app-backend)
- **REST API** - FastAPI with automatic OpenAPI documentation

## Tech Stack

- **Python 3.11** with FastAPI
- **PostgreSQL** with SQLAlchemy 2.0 async
- **Pydantic v2** for validation

## Quick Start

```bash
# Set environment variables
export DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/bloom_db"
export SECRET_KEY="your-secret-key-at-least-32-characters"

# Install and run
pip install .
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

API docs available at `http://localhost:8000/api/docs`

## Production bootstrap

Bloom now rejects unsafe bootstrap defaults in production mode.

Set at least these values before starting a release deployment:

```env
BLOOM_ENV=production
SECRET_KEY=<strong-random-secret-at-least-32-chars>
ADMIN_EMAIL=<real-admin-email>
ADMIN_PASSWORD=<strong-admin-password-at-least-16-chars>
```

Startup fails in production if any of these are still using bootstrap defaults:

- `ADMIN_EMAIL=admin@example.com`
- `ADMIN_PASSWORD=changeme123`
- admin password shorter than 16 characters

### First admin bootstrap

1. Set `BLOOM_ENV=production` and the admin variables above.
2. Start the backend once.
3. The startup seed promotes or creates the configured admin user.
4. Sign in as that admin and create invitation-based user accounts for maintainers and externals.

### Password rotation

Rotate the bootstrap admin password by:

1. generating a new strong password,
2. updating `ADMIN_PASSWORD` in the deployment secret or environment,
3. restarting the backend so the seeded admin account is updated,
4. verifying login with the new credential,
5. revoking or removing any old shared storage of the previous password.

## Invitation and SMTP configuration

Bloom now supports admin-only invitations with separate password setup and email verification.
Configure runtime values via environment variables or `.env`:

- `APP_BASE_URL`
- `FRONTEND_BASE_URL`
- `SMTP_ENABLED`
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `SMTP_FROM_EMAIL`
- `SMTP_FROM_NAME`
- `SMTP_REPLY_TO`
- `SMTP_STARTTLS`
- `SMTP_SSL`
- `SMTP_TIMEOUT_SECONDS`
- `INVITE_TOKEN_TTL_HOURS`
- `EMAIL_VERIFICATION_TOKEN_TTL_HOURS`
- `PASSWORD_RESET_TOKEN_TTL_HOURS`

New auth endpoints:

- `POST /api/users/invite`
- `POST /api/users/{id}/resend-invite`
- `POST /api/users/{id}/revoke-invite`
- `GET /api/auth/invite-info?token=...`
- `POST /api/auth/accept-invite`
- `POST /api/auth/verify-email`
- `POST /api/auth/resend-verification`
- `POST /api/auth/forgot-password`
- `POST /api/auth/reset-password`

Frontend public routes expected by email links:

- `/accept-invite?token=...`
- `/verify-email?token=...`
- `/reset-password?token=...`

## API Endpoints

| Path | Description |
|------|-------------|
| `GET /api/health` | Health check |
| `GET /api/version` | Version info |
| `GET/POST /api/projects` | List/Create projects |
| `GET/POST /api/requirements` | List/Create requirements |
| `POST /api/requirements/{id}/link-testcase` | Link test case to requirement |
| `POST /api/requirements/{id}/link-testrun` | Link external test run to requirement |
| `GET/POST /api/test-cases` | List/Create test cases |
| `GET /api/traceability` | Traceability matrix by project |

## Docker

```bash
docker build -t bloom-backend .
docker run -p 8000:8000 -e DATABASE_URL=... -e SECRET_KEY=... bloom-backend
```

## Part of EmbedLabs Suite

- **[Bud](https://github.com/MbedLabs/bud-app-backend)** - Test Station Manager (test execution platform)
- **[Bloom](https://github.com/MbedLabs/bloom-app-backend)** - Lifecycle Manager (this repo)

## License

This project is licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0)**. See the [LICENSE](LICENSE) file for the full text.

Copyright (C) 2026 EmbedLabs.

For commercial licensing options that do not require AGPL compliance, contact dev@embedlabs.net. Contributions are accepted under the [CLA](CLA.md) — see [CONTRIBUTING.md](CONTRIBUTING.md).
