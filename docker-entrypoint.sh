#!/bin/sh
set -e

# If starting the web server, automatically run migrations first
if [ "$1" = "uvicorn" ] || [ -z "$1" ]; then
    echo "==> Running Alembic migrations (alembic upgrade head)..."
    alembic upgrade head
    echo "==> Migrations applied successfully."
fi

# Default command if none provided
if [ -z "$1" ]; then
    set -- uvicorn app.main:app --host 0.0.0.0 --port 8000
fi

exec "$@"
