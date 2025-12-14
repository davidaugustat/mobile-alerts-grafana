#!/usr/bin/env bash
set -euo pipefail

# Require docker-compose file as first argument
if [ $# -lt 1 ] || [ -z "${1:-}" ]; then
  echo "Usage: $0 <docker-compose-file>" >&2
  echo "Example: $0 docker-compose.ports.yml" >&2
  exit 1
fi
COMPOSE_FILE="$1"
shift

# Load environment variables
if [ -f ".env" ]; then
  set -a
  # shellcheck disable=SC1091
  . ".env"
  set +a
fi

# Require necessary env vars
require_var() {
  local name="$1"
  if [ -z "${!name:-}" ]; then
    echo "Error: Required environment variable '$name' is not set or empty." >&2
    exit 1
  fi
}
require_var DB_USER
require_var DB_PASSWORD
require_var DB_NAME

EXPORT_DIR="./exports"
mkdir -p "$EXPORT_DIR"

TIMESTAMP="$(date +'%Y%m%d-%H%M%S')"
FILENAME="${EXPORT_DIR}/measurements-${TIMESTAMP}.csv"

echo "Exporting measurements table to CSV: ${FILENAME}"

# Uses psql inside the timescaledb container and streams the result to stdout.
# Requires Docker Compose v2 (`docker compose`); change to `docker-compose` if needed.
docker compose -f "$COMPOSE_FILE" exec -T \
  -e PGPASSWORD="${DB_PASSWORD}" \
  timescaledb \
  psql \
    -U "${DB_USER}" \
    -d "${DB_NAME}" \
    -c "\copy (SELECT * FROM measurements ORDER BY time) TO STDOUT WITH CSV HEADER" \
    > "${FILENAME}"

echo "CSV export completed."
