# MCF

Singapore hiring-market intelligence platform built on [MyCareersFuture.sg](https://www.mycareersfuture.gov.sg/) data.

Scrapes the full MCF job archive (2019–present, ~6M listings), builds hybrid BM25 + FAISS search indexes, and serves an analytics dashboard with market trends, profile matching, and explainable NLP ranking.

## Product Tour

### Overview

![Overview dashboard](output/playwright/overview-dashboard.png)

### Trends Explorer

![Trends Explorer](output/playwright/trends-explorer.png)

### Match Lab

![Match Lab](output/playwright/match-lab-results.png)

### Search & Similarity

![Search and Similarity](output/playwright/search-similarity.png)

## What it does

- **Market Intelligence** — headline metrics, rising skills/companies, salary movement, and monthly trend comparisons
- **Hybrid Search** — FAISS vector similarity + BM25 keyword matching with skill-cluster query expansion and "why this matched" breakdowns
- **Profile Matching** — paste a resume summary, get ranked jobs with fit scores across semantic similarity, skill overlap, seniority, and salary
- **Historical Archive** — enumerate every MCF job ID from 2019–present with per-ID tracking, gap detection, and targeted retries
- **Daemon Scraping** — background process with adaptive rate limiting, sleep/wake detection, and automatic checkpointing
- **Docker Deploy** — single `docker compose up` for the full stack (API + React frontend behind nginx)

## Tech stack

| Layer | Technologies |
|-------|-------------|
| **Backend** | Python · FastAPI · SQLite/PostgreSQL · httpx · Pydantic · Typer |
| **Search** | ONNX Runtime · transformers · FAISS · pgvector · BM25/FTS · scikit-learn |
| **Frontend** | React · Vite · TypeScript · Recharts · Tailwind CSS |
| **Infrastructure** | Docker Compose · nginx · uvicorn · Poetry |

## Quick start

```bash
poetry install --with ml,ml_torch
poetry run python -m src.cli scrape "data scientist"
# Export the default ONNX bundle once for local CLI usage.
poetry run python -m src.cli embed-export-onnx all-MiniLM-L6-v2 --output-dir data/models/all-MiniLM-L6-v2-onnx
poetry run python -m src.cli embed-generate
poetry run python -m src.cli api-serve --reload    # Swagger UI at localhost:8000/docs
cd src/frontend && npm install && npm run dev       # Frontend at localhost:5173

# Or run everything with Docker
# The backend image exports and bundles the default ONNX model during build.
docker compose build backend
# Rebuild embeddings/indexes inside the container so they match the bundled ONNX runtime.
docker compose run --rm backend python -m src.cli embed-generate --no-skip-existing
docker compose up
```

The first Docker backend build is slower because it downloads and exports the bundled ONNX model once. After that, Docker deployments no longer depend on a host-side `data/models/...` bundle.

> **Tip:** `alias mcf="poetry run python -m src.cli"` — then `mcf scrape`, `mcf search`, etc.

## PostgreSQL rollout

Local development can now target either a SQLite path or a PostgreSQL DSN via `--db`, `MCF_DB_PATH`, or `DATABASE_URL`.

```bash
# 1. Create and verify a hot backup before touching the live SQLite file.
poetry run python -m src.cli db-backup --source data/mcf_jobs.db --backup-dir data/backups

# 2. Load a verified SQLite backup into local Postgres.
poetry run python -m src.cli pg-migrate \
  --source data/backups/mcf_pre_postgres_20260324T191812.db \
  --target postgresql://postgres:postgres@localhost:5432/mcf

# 3. Serve locally from Postgres.
#    If local pgvector is unavailable, embeddings are stored as BYTEA and FAISS remains the local vector path.
poetry run python -m src.cli api-serve \
  --db postgresql://postgres:postgres@localhost:5432/mcf \
  --search-backend faiss

# 4. Persist the local Postgres target so plain daemon commands default to it.
printf '%s\n' 'postgresql://postgres@127.0.0.1:55432/mcf' > data/default_db_target.txt

# 5. Seed and maintain a lean hosted slice (2026 + last 90 days, job vectors only).
poetry run python -m src.cli pg-seed-hosted \
  --source postgresql://postgres:postgres@localhost:5432/mcf \
  --target postgresql://<neon-dsn>
poetry run python -m src.cli pg-purge-hosted --target postgresql://<neon-dsn>
```

The hosted slice intentionally excludes skill and company embeddings. Local Postgres keeps the full archive, while FAISS remains available for local/offline search during the transition. The daemon now checks `data/default_db_target.txt` when `--db` is omitted, so a migrated local Postgres DSN can become the default without requiring shell exports.

For the full hosted deployment recipe, see [docs/neon-oracle-hosted-deploy.md](docs/neon-oracle-hosted-deploy.md). That guide covers Neon Free for Postgres, GitHub Actions for scheduled hosted refreshes, and Oracle Cloud Always Free for the API container.

## Architecture

```
src/
├── api/                 # FastAPI REST API (routes, models, middleware)
├── mcf/                 # Core scraper + storage package
│   ├── embeddings/      # Hybrid search engine (FAISS, BM25, query expansion)
│   ├── api_client.py    # Async HTTP client with retry
│   ├── database.py      # SQLite operations + history tracking
│   ├── historical_scraper.py  # Full-archive enumeration by job ID
│   ├── adaptive_rate.py # Dynamic rate limiting (backs off on 429s)
│   ├── daemon.py        # Background process with wake detection
│   └── batch_logger.py  # Buffered per-ID attempt tracking
├── frontend/            # React + Vite SPA
├── cli.py               # Typer CLI (run --help for full command list)
└── legacy/              # Old Selenium scrapers
```

## API

The REST API serves hybrid search, profile matching, market trends, and company intelligence. Start with `python -m src.cli api-serve` and explore the interactive docs at [`/docs`](http://localhost:8000/docs).

## Development

```bash
poetry install --with ml,ml_torch
poetry run pytest
python -m src.cli scrape "test" -v
```

## License

MIT
