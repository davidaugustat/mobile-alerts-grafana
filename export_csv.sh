#!/usr/bin/env bash
set -euo pipefail

EXPORT_DIR="./exports"
mkdir -p "$EXPORT_DIR"

TIMESTAMP="$(date +'%Y%m%d-%H%M%S')"
FILENAME="${EXPORT_DIR}/measurements-${TIMESTAMP}.csv"

echo "Exporting measurements table to CSV: ${FILENAME}"

# Uses psql inside the timescaledb container and streams the result to stdout.
# Requires Docker Compose v2 (`docker compose`); change to `docker-compose` if needed.
docker compose exec -T \
  -e PGPASSWORD="sensor_password" \
  timescaledb \
  psql \
    -U sensor_user \
    -d sensor_data \
    -c "\copy (SELECT * FROM measurements ORDER BY time) TO STDOUT WITH CSV HEADER" \
    > "${FILENAME}"

echo "CSV export completed."
