"""Sync `room_assoc` table from a YAML config file and exit.

Expected YAML structure:

associations:
  - sensor_id: 0123456789AB
    room_id: living-room
    start_date: 2024-01-01T00:00:00Z    # optional, ISO timestamp or omitted/null
    end_date: 2025-06-01T00:00:00Z      # optional, ISO timestamp or null = until now

If the file is valid, the script replaces the contents of `room_assoc` with the list
from the file (simple authoritative sync).
"""

import argparse
import logging
import os
from typing import Dict, List, Optional

import yaml
import psycopg2
from psycopg2.extras import execute_values


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

DB_HOST = os.getenv("DB_HOST", "timescaledb")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")


def check_env_vars() -> None:
    missing = [k for k in ("DB_NAME", "DB_USER", "DB_PASSWORD") if not os.getenv(k)]
    if missing:
        logging.error("Missing required environment variables: %s", ", ".join(missing))
        raise SystemExit(2)


def load_config(path: str) -> List[Dict[str, Optional[str]]]:
    logging.info("Loading YAML config from %s", path)
    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    if not data:
        return []

    associations = data.get("associations")
    if associations is None:
        raise ValueError("YAML config must contain top-level key 'associations'")

    out = []
    for i, a in enumerate(associations):
        if not isinstance(a, dict):
            raise ValueError(f"association #{i} is not a mapping")
        sensor_id = a.get("sensor_id")
        room_id = a.get("room_id")
        start_date = a.get("start_date")
        end_date = a.get("end_date")
        if not sensor_id or not room_id:
            raise ValueError(f"association #{i} missing sensor_id or room_id")
        out.append({
            "sensor_id": sensor_id,
            "room_id": room_id,
            "start_date": start_date,
            "end_date": end_date,
        })

    return out


import time

def get_db_connection(retries: int = 12, wait_seconds: int = 5):
    """Try to connect to the database with retries and backoff."""
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            logging.info("Attempting DB connection (%d/%d)...", attempt, retries)
            conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD)
            conn.autocommit = False
            logging.info("Connected to database.")
            return conn
        except Exception as e:
            last_exc = e
            logging.warning("Database connection failed: %s", e)
            if attempt < retries:
                logging.info("Retrying in %d seconds...", wait_seconds)
                time.sleep(wait_seconds)
    logging.error("Could not connect to database after %d attempts", retries)
    raise last_exc


def sync_to_db(entries: List[Dict[str, Optional[str]]]) -> None:
    logging.info("Connecting to DB %s@%s:%s", DB_NAME, DB_HOST, DB_PORT)
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            logging.info("Ensuring 'room_assoc' table exists")
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS room_assoc (
                    sensor_id TEXT NOT NULL,
                    room_id   TEXT NOT NULL,
                    start_date TIMESTAMPTZ NULL,
                    end_date   TIMESTAMPTZ NULL
                )
                """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS idx_room_assoc_sensor ON room_assoc (sensor_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_room_assoc_room ON room_assoc (room_id)")

            logging.info("Truncating existing 'room_assoc' table")
            cur.execute("TRUNCATE room_assoc")

            if entries:
                logging.info("Inserting %d association(s)", len(entries))
                records = [
                    (e["sensor_id"], e["room_id"], e["start_date"], e["end_date"]) for e in entries
                ]
                execute_values(
                    cur,
                    "INSERT INTO room_assoc (sensor_id, room_id, start_date, end_date) VALUES %s",
                    records,
                    template=None,
                    page_size=100,
                )
            else:
                logging.info("No entries to insert; leaving table empty")
        conn.commit()
        logging.info("Sync completed successfully")
    except Exception as e:
        conn.rollback()
        logging.exception("Database sync failed. Rolled back. Exception: %s", e)
        raise
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync room associations to DB from a YAML file")
    parser.add_argument("config", nargs="?", default=os.getenv("ROOM_ASSOC_CONFIG", "/config/room_assoc.yml"), help="Path to YAML config")
    args = parser.parse_args()

    check_env_vars()

    if not os.path.exists(args.config):
        logging.warning(
            "Config file not found: %s. No room associations will be synced. "
            "This is okay if you do not need room associations. "
            "If you want to manage room associations, please create the room_assoc.yml file.",
            args.config,
        )
        return 0

    try:
        entries = load_config(args.config)
    except Exception as e:
        logging.error("Failed to parse config: %s", e)
        return 3

    try:
        sync_to_db(entries)
    except Exception:
        return 4

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
