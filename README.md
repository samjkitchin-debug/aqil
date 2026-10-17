# Aqil

Human-centred investment intelligence and long-term wealth-building platform (monorepo).

## Prerequisites

- Git
- Node.js 24 LTS (this repo targets Node 24; [nvm-windows](https://github.com/coreybutler/nvm-windows) is supported)
- npm
- Python 3.13
- [uv](https://docs.astral.sh/uv/) for the research worker
- Supabase project (configure later — not required for initial UI scaffolding)

## Repository layout

| Path | Purpose |
|------|---------|
| `apps/web` | Next.js App Router PWA |
| `workers/research` | Python research and analytics engine |
| `supabase/migrations` | PostgreSQL migrations (Supabase CLI) |
| `packages/contracts` | Versioned JSON Schemas (mirror of `docs/schemas`) |
| `docs` | Product and engineering specifications |
| `tests` | Shared fixtures and future integration tests |

## First-time setup

```powershell
# From repository root
nvm use 24.12.0   # or your installed Node 24.x

cd apps/web
copy .env.example .env.local
npm install

cd ../../workers/research
uv sync
```

## Development

```powershell
# Web application (from repository root)
npm run dev
```

The app runs at [http://localhost:3000](http://localhost:3000).

### Research worker

```powershell
cd workers/research
uv run pytest
uv run ruff check .
```

## Quality checks

```powershell
# From repository root
npm run build
npm run typecheck
npm run lint
npm run test:research
npm run check:tokens
npm run test:e2e
npm run test:db
```

Database workflow: `supabase/migrations/`, `npm run db:reset`, `npm run db:test`, `npm run db:types` (requires Docker Desktop locally).

Responsive layout contract: `docs/RESPONSIVE_LAYOUT_CONTRACT.md`.
```

## Environment variables

See `apps/web/.env.example`. Public Supabase keys are prefixed with `NEXT_PUBLIC_`. The service role key must only be set in server-side environments.

## Documentation

Product requirements will be added under `docs/`. Until then, avoid inventing detailed product behaviour in code.

## Deployment

Vercel deployment will target `apps/web` (configuration to be added when hosting is set up).
