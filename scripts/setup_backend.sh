#!/usr/bin/env bash
# One-shot local setup for the backend.
# Assumes: Python 3.11+, a running PostgreSQL on localhost:5432 with the
# database/user from .env created. If you prefer Docker, just run
# `docker compose up` from the repo root instead.

set -euo pipefail

cd "$(dirname "$0")/../backend"

if [ ! -f .env ]; then
    echo ">> Creating .env from .env.example"
    cp .env.example .env
fi

if [ ! -d .venv ]; then
    echo ">> Creating virtualenv"
    python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

echo ">> Installing dependencies"
pip install --upgrade pip > /dev/null
pip install -e ".[dev]"

echo ">> Applying migrations"
alembic upgrade head

echo ">> Seeding data"
python -m app.db.seed

echo
echo "Done. Start the API with:"
echo "  cd backend && source .venv/bin/activate && uvicorn app.main:app --reload"
