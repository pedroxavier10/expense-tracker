#!/usr/bin/env bash
# One-shot local setup for the backend.
# Assumes: Python 3.11+, uv, and a running PostgreSQL accessible at the
# DATABASE_URL in .env (default port 5466 — run `docker compose up db` for
# that, or set port 5432 for a local PostgreSQL install).
# If you prefer Docker for everything, run `docker compose up` instead.

set -euo pipefail

cd "$(dirname "$0")/../backend"

if [ ! -f .env ]; then
    echo ">> Creating .env from .env.example"
    cp .env.example .env
fi

if [ ! -d .venv ]; then
    echo ">> Creating virtualenv"
    uv venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

echo ">> Installing dependencies"
uv pip install -e ".[dev]"

echo ">> Applying migrations"
alembic upgrade head

echo ">> Seeding data"
python -m app.db.seed

echo
echo "Done. Start the API with:"
echo "  cd backend && source .venv/bin/activate && uvicorn app.main:app --reload"
