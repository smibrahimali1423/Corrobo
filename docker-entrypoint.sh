#!/bin/sh
# Apply DB migrations before starting the app, so a new image with a new
# migration upgrades the schema on deploy. Alembic is a no-op when up to date.
set -e

alembic upgrade head

if [ "${SEED_DEMO:-false}" = "true" ]; then
  python seed.py
fi

exec "$@"
