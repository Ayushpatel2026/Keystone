# Keystone backend

The API for Keystone, built with FastAPI and PostgreSQL.

## Running it

You need Docker, [uv](https://docs.astral.sh/uv/), and a `.env` file in this
folder with `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`,
`KEYSTONE_DATABASE_URL` and `KEYSTONE_SECRET_KEY`. Then, in this folder:

```powershell
docker compose up -d --wait
uv run alembic upgrade head
uv run python -m app.core.seed
uv run uvicorn app.main:app --reload --port 8000
```

The middle two are only needed the first time, and after pulling new
migrations. Every seeded user has the password `dev-password-123`.

## Resetting the demo data

The seed script only adds what's missing, so it won't undo applications made
during a run-through. To start over from the seeded state, stop the backend and
run this in this folder:

```powershell
docker compose down -v
docker compose up -d --wait
uv run alembic upgrade head
uv run python -m app.core.seed
```

`down -v` deletes the local database volume, so only do this against your own
dev database. Then start the backend again.
