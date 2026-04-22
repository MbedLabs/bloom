# EmbedLabs Bloom - Product Lifecycle Management

Frontend for **Bloom**, EmbedLabs' requirements and lifecycle management platform. A PLM interface for managing requirements, test cases, and traceability across the product lifecycle.

## Features

- **Dashboard** - Overview of projects, requirements, test cases, and coverage metrics
- **Project Management** - Create and organize projects with requirements and test cases
- **Requirement Editor** - Hierarchical requirements with status tracking (Draft → Verified)
- **Test Case Editor** - Structured test cases with steps, preconditions, and requirement linking
- **Traceability Matrix** - Visual coverage tracking across all requirements
- **Test Station Links** - Direct links to test runs in the Bud TMP

## Tech Stack

- **React 18** with TypeScript
- **Vite 5** build tool
- **Tailwind CSS** with EmbedLabs teal theme
- **TanStack Query** for data fetching
- **Lucide** icons

## Quick Start

```bash
npm install
npm run dev
```

App runs at `http://localhost:3001` with API proxy to `localhost:8000`.

## Deployment

This frontend is designed to be environment-agnostic using runtime configuration injection.

### Environment Variables

| Variable | Description | Default |
| :--- | :--- | :--- |
| `BACKEND_UPSTREAM` | Nginx upstream for the API proxy (`/api`) | `bloom-backend.bloom.svc.cluster.local:8000` |
| `BUD_APP_URL` | URL of the Bud TMP (for sidebar links) | `http://localhost:3000` |
| `BLOOM_APP_URL` | Public URL of this Bloom instance (for self-referencing) | `http://localhost:3001` |

### Docker

```bash
docker build -t bloom-app-frontend .

# Run with custom upstream and cross-links
docker run -p 8081:80 \
  -e BACKEND_UPSTREAM=backend:8000 \
  -e BUD_APP_URL=https://bud.example.com \
  bloom-app-frontend
```

## Part of EmbedLabs Suite

- **[Bud](https://github.com/MbedLabs/bud-app-frontend)** - Test Station Manager (test execution platform)
- **[Bloom](https://github.com/MbedLabs/bloom-app-frontend)** - PLM (this repo)

## License

This project is licensed under the **GNU Affero General Public License v3.0 or later (AGPL-3.0-or-later)**. See the [LICENSE](LICENSE) file for the full text.

Copyright (C) 2024-2026 EmbedLabs.

For commercial licensing options that do not require AGPL compliance, contact dev@embedlabs.de. Contributions are accepted under the [CLA](CLA.md) — see [CONTRIBUTING.md](CONTRIBUTING.md).
