# Superset Dashboard Migrator

A small, stateless web app that rewrites [Apache Superset](https://superset.apache.org/) dashboard export ZIPs so you can move dashboards between environments (for example dev → QA → prod).

It remaps database connection URIs and schema names, rewrites schema-qualified table references in dataset SQL (including CTEs), and backfills missing chart UUIDs on dashboard layouts so import remapping works.

**This is a local / trusted-network tool.** It does not include authentication. Anyone who can reach the process can upload exports and submit target connection strings. Do not expose it to the public internet.

## Features

- Upload a Superset dashboard export ZIP and inspect detected databases and schemas
- Map each source connection to a target SQLAlchemy URI and optional new database name
- Map source schemas to target schemas
- Patch dataset SQL, including `FROM` / `JOIN` references inside `WITH` / `WITH RECURSIVE` CTEs and `schema.table.column` expressions
- Backfill missing `meta.uuid` values on dashboard chart tiles
- Download a new ZIP ready to import into the target Superset instance
- Single Docker image: FastAPI serves the built React UI

## What it does not do

- Talk to Superset over the API (no auto-export or auto-import)
- Rewrite chart metrics, calculated columns, or dashboard filter configs
- Authenticate users or persist uploads (everything stays in memory for one request)

## Quick start

### Docker (recommended)

```bash
docker compose up --build
```

Open [http://localhost:8000](http://localhost:8000).

The container publishes a liveness probe at `/health` (also at `/api/health`).

### Run locally

**Backend**

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py                   # http://localhost:8000
```

**Frontend** (separate terminal, for development)

```bash
cd frontend
npm ci
npm run dev                      # http://localhost:5173, proxies /api to :8000
```

## How to use it

1. In the source Superset, export one or more dashboards (ZIP).
2. Upload that ZIP in the app and analyse it.
3. Fill in the target connection URI(s) and schema name(s).
4. Click **Transform & Download**.
5. In the target Superset, import the downloaded ZIP (**Dashboards → Import**).

Superset masks passwords in exported `sqlalchemy_uri` values. You must enter real target credentials. Those credentials are written into the output ZIP and are sent to the server for that request — treat the ZIP as a secret.

## What gets changed

| File | Field | Action |
|------|-------|--------|
| `databases/*.yaml` | `sqlalchemy_uri` | Replaced with the target URI |
| `databases/*.yaml` | `database_name` | Updated if the target name differs |
| `datasets/**/*.yaml` | `schema` | Replaced with the target schema |
| `datasets/**/*.yaml` | `sql` | Schema-qualified table refs rewritten (including CTE bodies) |
| `datasets/<db>/` | folder name | Renamed if `database_name` changes |
| `charts/*.yaml` | — | Unchanged (charts reference dataset UUIDs) |
| `dashboards/*.yaml` | `position` CHART `meta.uuid` | Backfilled when missing (needed for import remapping) |

## Health check

```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

Docker and Compose use this endpoint as the container healthcheck.

## Limitations

- SQL rewriting is pattern-based, not a full SQL parser. It covers keyword-prefixed refs (`FROM` / `JOIN` / `UPDATE` / `INTO` / `TABLE`) and `schema.table.column` expressions, and it skips CTE names so a CTE that happens to share a schema name is left alone. Unusual dialect syntax may still be missed.
- There is no authentication. Run it on localhost or a trusted network only.
- Uploads are held in memory. Very large ZIPs can exhaust process memory.

## Tests

```bash
cd backend
python -m unittest tests.test_sql_schema -v
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for local setup, tests, and pull-request guidelines.

## Project layout

```
superset-migrator/
  backend/           FastAPI app, parse/transform logic
  frontend/          Vite + React UI
  Dockerfile         Multi-stage image (Node build → Python runtime)
  docker-compose.yml Single-service deploy
```

## License

This project is licensed under the [MIT License](LICENSE).
