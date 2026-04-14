# EmbedLabs Bloom - Application Lifecycle Management

Frontend for **Bloom**, EmbedLabs' requirements and lifecycle management platform. A Polarion-like interface for managing requirements, test cases, and traceability across the product lifecycle.

## Features

- **Dashboard** - Overview of projects, requirements, test cases, and coverage metrics
- **Project Management** - Create and organize projects with requirements and test cases
- **Requirement Editor** - Hierarchical requirements with status tracking (Draft → Verified)
- **Test Case Editor** - Structured test cases with steps, preconditions, and requirement linking
- **Traceability Matrix** - Visual coverage tracking across all requirements
- **Test Station Links** - Direct links to test runs in the Bud Test Station app

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

App runs at `http://localhost:3000` with API proxy to `localhost:8000`.

## Docker

```bash
docker build -t bloom-frontend .
docker run -p 3000:80 bloom-frontend
```

## Part of EmbedLabs Suite

- **[Bud](https://github.com/elomariamin/bud-app-frontend)** - Test Station Manager (test execution platform)
- **[Bloom](https://github.com/elomariamin/bloom-app-frontend)** - Lifecycle Manager (this repo)
