#!/usr/bin/env python3
import os
import sys
import logging
from datetime import datetime, timezone, timedelta

import psycopg2
from psycopg2 import OperationalError

"""
Healthcheck Script for Monitoring Sensor Data

This script fails if no new sensor measurements have been recorded for at least 30 minutes.
"""

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

DB_HOST = os.getenv("DB_HOST", "timescaledb")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

SENSOR_IDS_ENV = os.getenv("SENSOR_IDS", "")

THRESHOLD_MINUTES = 30

def parse_sensor_ids(env_value: str):
    if not env_value:
        return []
    return [s.strip() for s in env_value.split(",") if s.strip()]

def fail(msg: str) -> None:
    logging.error(msg)
    sys.exit(1)

def ok(msg: str) -> None:
    logging.info(msg)
    sys.exit(0)

def connect_db():
    if not DB_NAME or not DB_USER or not DB_PASSWORD:
        fail("Missing DB credentials in environment for healthcheck.")
    try:
        return psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            connect_timeout=5,
        )
    except OperationalError as e:
        fail(f"DB connection failed: {e}")

def main():
    sensors = parse_sensor_ids(SENSOR_IDS_ENV)
    if not sensors:
        ok("No SENSOR_IDS configured -> healthcheck OK (nothing to check).")

    conn = connect_db()
    try:
        with conn.cursor() as cur:
            now = datetime.now(timezone.utc)
            threshold = timedelta(minutes=THRESHOLD_MINUTES)

            recent_count = 0
            for sensor in sensors:
                cur.execute("SELECT MAX(time) FROM measurements WHERE sensor_id = %s", (sensor,))
                row = cur.fetchone()
                last_ts = row[0] if row else None

                if last_ts is None:
                    # treat missing data as stale
                    logging.info("Sensor '%s' has no measurements (treated as stale).", sensor)
                    continue

                # ensure timezone-aware datetime
                if last_ts.tzinfo is None:
                    last_ts = last_ts.replace(tzinfo=timezone.utc)
                age = now - last_ts

                if age <= threshold:
                    logging.info("Sensor '%s' last measurement is %s old -> recent.", sensor, age)
                    recent_count += 1
                else:
                    logging.info("Sensor '%s' last measurement is %s old -> stale.", sensor, age)

            if recent_count > 0:
                ok(f"{recent_count}/{len(sensors)} sensors have recent measurements -> healthy.")
            else:
                fail(f"No sensors have measurements within {threshold} -> unhealthy.")
    finally:
        try:
            conn.close()
        except Exception:
            pass

if __name__ == "__main__":
    main()
