#!/usr/bin/env bash
# Apply all Supabase SQL migrations in numeric order.
# Usage: DATABASE_URL=<url> bash backend/scripts/run_migrations.sh
set -euo pipefail

MIGRATIONS_DIR="$(dirname "$0")/../app/db/migrations"

if [ -z "${DATABASE_URL:-}" ]; then
  echo "ERROR: DATABASE_URL environment variable is not set."
  exit 1
fi

echo "Applying Apex migrations from $MIGRATIONS_DIR"

for f in $(ls "$MIGRATIONS_DIR"/*.sql | sort -V); do
  echo "  → Applying $(basename "$f")..."
  psql "$DATABASE_URL" -f "$f"
done

echo "All migrations applied successfully."
