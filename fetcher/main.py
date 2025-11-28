import logging
import os
import time
from datetime import datetime, timezone
from typing import List, Optional

import psycopg2
from psycopg2 import OperationalError, InterfaceError
from psycopg2.extensions import connection as PgConnection

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

DB_HOST = os.getenv("DB_HOST", "timescaledb")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "sensor_data")
DB_USER = os.getenv("DB_USER", "sensor_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "sensor_password")

FETCH_INTERVAL_SECONDS = int(os.getenv("FETCH_INTERVAL_SECONDS", "300"))

# Comma-separated list of sensor IDs, e.g. "sensor1,sensor2"
SENSOR_IDS_ENV = os.getenv("SENSOR_IDS", "")

_conn: Optional[PgConnection] = None


def get_db_connection() -> PgConnection:
    """
    Returns a reusable PostgreSQL connection.
    If the connection is closed or fails, it retries until it can connect.
    """
    global _conn

    if _conn is not None and not _conn.closed:
        return _conn

    while True:
        try:
            logging.info("Connecting to TimescaleDB at %s:%s ...", DB_HOST, DB_PORT)
            _conn = psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
            )
            _conn.autocommit = True
            logging.info("Connected to TimescaleDB.")
            return _conn
        except OperationalError as e:
            logging.error("Database connection failed: %s", e)
            logging.info("Retrying in 5 seconds ...")
            time.sleep(5)


def insert_into_db(
    timestamp: datetime,
    sensor_id: str,
    t1: float,
    t2: Optional[float],
) -> None:
    """
    Insert a single measurement row into the TimescaleDB 'measurements' hypertable.

    :param timestamp: datetime (preferably timezone-aware, e.g. UTC)
    :param sensor_id: ID of the sensor (string)
    :param t1: temperature reading for t1 (float)
    :param t2: temperature reading for t2 (float or None if not available)
    """
    global _conn

    sql = """
        INSERT INTO measurements (time, sensor_id, t1, t2)
        VALUES (%s, %s, %s, %s)
    """

    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(sql, (timestamp, sensor_id, t1, t2))
    except (OperationalError, InterfaceError) as e:
        logging.warning("DB connection issue when inserting; retrying once. Error: %s", e)
        # Force reconnection on next call
        if _conn is not None:
            try:
                _conn.close()
            except Exception:
                pass
            _conn = None

        # Retry once
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(sql, (timestamp, sensor_id, t1, t2))


def fetch_data(sensor_ids: List[str]) -> None:
    """
    Placeholder function for fetching logic.

    Implement this function yourself. It should:
      - query your custom HTTP/JSON API for each sensor_id
      - obtain timestamp, t1, and (optionally) t2
      - call insert_into_db(timestamp, sensor_id, t1, t2) for each measurement

    Example skeleton:

        from datetime import datetime, timezone
        import requests

        def fetch_data(sensor_ids: List[str]) -> None:
            for sensor_id in sensor_ids:
                # Call your API, e.g.:
                # resp = requests.get(f"http://your-api/sensors/{sensor_id}")
                # data = resp.json()
                #
                # timestamp = datetime.fromisoformat(data["time"]).astimezone(timezone.utc)
                # t1 = float(data["t1"])
                # t2 = float(data.get("t2")) if "t2" in data else None
                #
                # insert_into_db(timestamp, sensor_id, t1, t2)
                pass
    """
    # Placeholder; you will implement this.
    pass


def parse_sensor_ids(env_value: str) -> List[str]:
    if not env_value:
        return []
    return [s.strip() for s in env_value.split(",") if s.strip()]


def main() -> None:
    sensor_ids = parse_sensor_ids(SENSOR_IDS_ENV)
    if not sensor_ids:
        logging.warning("No SENSOR_IDS configured. No sensors will be polled.")

    logging.info(
        "Fetcher starting. Interval: %d seconds. Sensors: %s",
        FETCH_INTERVAL_SECONDS,
        ", ".join(sensor_ids) if sensor_ids else "(none)",
    )

    while True:
        cycle_start = time.time()
        logging.info("Starting fetch cycle ...")

        try:
            fetch_data(sensor_ids)
        except Exception:
            logging.exception("Unhandled exception in fetch_data")

        elapsed = time.time() - cycle_start
        sleep_for = max(0, FETCH_INTERVAL_SECONDS - elapsed)
        logging.info("Fetch cycle finished (%.2f s). Sleeping for %.2f s.", elapsed, sleep_for)
        time.sleep(sleep_for)


if __name__ == "__main__":
    main()
