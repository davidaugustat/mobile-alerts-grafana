import logging
import os
import time
from datetime import datetime, timezone
from typing import List, Optional
import requests

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

# API documentation: https://mobile-alerts.eu/info/public_server_api_documentation.pdf
API_URL = "https://www.data199.com/api/pv1/device/lastmeasurement"

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
        ON CONFLICT (sensor_id, time) DO NOTHING
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


def _fetch_latest_measurements(sensor_ids: List[str]) -> Optional[dict]:
    """POST once to the Mobile Alerts API asking for the latest measurements.

    Returns parsed JSON dict on success, or None on failure. No retries.
    """
    if not sensor_ids:
        logging.info("No sensor IDs provided – skipping API call.")
        return None

    post_param = {"deviceids": ",".join(sensor_ids)}
    try:
        resp = requests.post(API_URL, data=post_param, timeout=10)
        if resp.status_code != 200:
            logging.warning(
                "API responded with status %d – body: %s",
                resp.status_code,
                resp.text[:300],
            )
            return None
        return resp.json()
    except requests.RequestException as e:
        logging.warning("Request exception: %s", e)
        return None


def _convert_timestamp(unix_ts: int) -> datetime:
    """Convert UNIX timestamp (seconds) to timezone-aware UTC datetime."""
    return datetime.fromtimestamp(unix_ts, tz=timezone.utc)


def fetch_data(sensor_ids: List[str]) -> None:
    """Fetch latest measurements for provided sensor IDs and insert into DB.

    Steps:
      1. Call API once for all sensor IDs.
      2. Validate success flag.
      3. For each device object, derive timestamp, temperatures.
      4. Insert using insert_into_db.
    """
    data = _fetch_latest_measurements(sensor_ids)
    if not data:
        logging.error("No data returned from API.")
        return

    if not data.get("success"):
        logging.error("API indicated failure: %s", data)
        return

    devices = data.get("devices", [])
    if not devices:
        logging.warning("API returned success but no devices.")
        return

    inserted = 0
    for device in devices:
        try:
            dev_id = device.get("deviceid")
            measurement = device.get("measurement", {})
            ts_unix = measurement.get("ts")
            if dev_id is None or ts_unix is None:
                logging.debug("Skipping device with missing id or timestamp: %s", device)
                continue
            timestamp = _convert_timestamp(ts_unix)
            t1 = measurement.get("t1")
            t2 = measurement.get("t2")
            if t1 is None and t2 is None:
                logging.debug("Skipping device %s – no temperature values", dev_id)
                continue
            insert_into_db(timestamp, dev_id, t1, t2)
            inserted += 1
        except Exception:
            logging.exception("Failed processing device object: %s", device)

    logging.info("Inserted %d measurements (received %d device objects).", inserted, len(devices))


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
