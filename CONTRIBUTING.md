# Contributing

Thanks for wanting to improve Superset Dashboard Migrator. This is a small, local-only tool. Keep changes focused and avoid adding authentication, persistence, or cloud-specific wiring unless that is the point of the PR.

## Development setup

**Backend**

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py                   # http://localhost:8000
```

**Frontend** (separate terminal)

```bash
cd frontend
npm ci
npm run dev                      # http://localhost:5173, proxies /api to :8000
```

**Docker**

```bash
docker compose up --build
```

Open [http://localhost:8000](http://localhost:8000). Health: `GET /health`.

Do not commit real Superset exports, connection URIs, or credentials.

## Tests

From `backend/`:

```bash
python -m unittest tests.test_sql_schema -v
```

If you change parse/transform behavior, add or update tests next to the code you touched.

## Pull requests

1. Fork the repo and create a branch from `main`.
2. Keep the diff small and explain *why* the change is needed.
3. Run the tests above. If you change SQL rewriting, include a fixture that covers the new pattern (CTEs, quoting, etc.).
4. Do not add company-specific hostnames, schema names, or sample data from a real environment.
5. Open a PR against `main` with a short summary and how you verified it (local, Docker, or both).

## Reporting issues

Include:

- Superset version the export came from (if you know it)
- What you expected vs what happened
- A **redacted** description of the ZIP layout (folder names, not URIs or SQL with credentials)

Never paste production connection strings or passwords into an issue.

## Security

This app is meant to run on localhost or a trusted network. It has no auth. If you find a vulnerability, please do not file a public issue with an exploit. Open a private report or contact the maintainer instead.
