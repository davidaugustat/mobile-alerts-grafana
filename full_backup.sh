#!/usr/bin/env bash
set -euo pipefail

# -----------------------------------------------------------------------------
# full_backup.sh
#
# Runs backup + export scripts for a given docker compose file and creates
# a ZIP archive containing:
#   - Latest *.sql file from backups/
#   - Latest *.csv file from exports/
#   - config/room_assoc.yml (if it exists)
#
# The archive is stored in ./full_backup/ and named:
#   full_backup_<timestamp>.zip
# Files inside the archive are stored at root level (no directories).
#
# Requirements:
#   - bash
#   - zip (checked at runtime)
#
# Usage:
#   ./full_backup.sh <compose-file>
#
# Example:
#   ./full_backup.sh docker-compose.traefik.yml
# -----------------------------------------------------------------------------

# Check arguments
if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <compose-file>" >&2
  exit 1
fi

COMPOSE_FILE="$1"
BACKUP_DIR="backups"
EXPORT_DIR="exports"
CONFIG_FILE="config/room_assoc.yml"
OUTPUT_DIR="full_backup"

# Check dependencies
if ! command -v zip >/dev/null 2>&1; then
  echo "Error: 'zip' command not found. Please install it." >&2
  exit 1
fi

# Validate compose file
if [[ ! -f "$COMPOSE_FILE" ]]; then
  echo "Error: compose file not found: $COMPOSE_FILE" >&2
  exit 1
fi

# Ensure output directory exists
mkdir -p "$OUTPUT_DIR"

# Run backup/export scripts
bash backup.sh "$COMPOSE_FILE"
bash export_csv.sh "$COMPOSE_FILE"

# Find latest files
latest_sql="$(ls -1t "$BACKUP_DIR"/*.sql 2>/dev/null | head -n 1)"
latest_csv="$(ls -1t "$EXPORT_DIR"/*.csv 2>/dev/null | head -n 1)"

# Validate required files exist
if [[ -z "${latest_sql:-}" ]]; then
  echo "Error: No .sql file found in $BACKUP_DIR" >&2
  exit 1
fi

if [[ -z "${latest_csv:-}" ]]; then
  echo "Error: No .csv file found in $EXPORT_DIR" >&2
  exit 1
fi

timestamp="$(date +%Y%m%d_%H%M%S)"
zip_name="${OUTPUT_DIR}/full_backup_${timestamp}.zip"

# Collect files to include
files=("$latest_sql" "$latest_csv")

if [[ -f "$CONFIG_FILE" ]]; then
  files+=("$CONFIG_FILE")
else
  echo "Warning: Optional file not found, skipping: $CONFIG_FILE"
fi

# -j removes directory paths inside the archive
zip -j "$zip_name" "${files[@]}"

echo "Created: $zip_name"
