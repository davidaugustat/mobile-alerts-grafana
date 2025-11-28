#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="./backups"
mkdir -p "$BACKUP_DIR"

TIMESTAMP="$(date +'%Y%m%d-%H%M%S')"
FILENAME="${BACKUP_DIR}/sensor_data-${TIMESTAMP}.sql"

echo "Creating backup: ${FILENAME}"

# Uses `pg_dump` inside the timescaledb container.
# Requires Docker Compose v2 (`docker compose`) or adjust to `docker-compose` if needed.
docker compose exec -T \
  -e PGPASSWORD="sensor_password" \
  timescaledb \
  pg_dump \
    -U sensor_user \
    -d sensor_data \
    -F p \
    > "${FILENAME}"

echo "Backup completed."
