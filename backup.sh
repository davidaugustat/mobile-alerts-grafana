#!/usr/bin/env bash
set -euo pipefail

# Load environment variables
if [ -f ".env" ]; then
  set -a
  # shellcheck disable=SC1091
  . ".env"
  set +a
fi

BACKUP_DIR="./backups"
mkdir -p "$BACKUP_DIR"

TIMESTAMP="$(date +'%Y%m%d-%H%M%S')"
FILENAME="${BACKUP_DIR}/sensor_data-${TIMESTAMP}.sql"

echo "Creating backup: ${FILENAME}"

# Uses `pg_dump` inside the timescaledb container.
# Requires Docker Compose v2 (`docker compose`) or adjust to `docker-compose` if needed.
docker compose exec -T \
  -e PGPASSWORD="${DB_PASSWORD}" \
  timescaledb \
  pg_dump \
    -U "${DB_USER}" \
    -d "${DB_NAME}" \
    -F p \
    > "${FILENAME}"

echo "Backup completed."
