-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Base table for measurements
CREATE TABLE IF NOT EXISTS measurements (
    time      TIMESTAMPTZ      NOT NULL,
    sensor_id TEXT             NOT NULL,
    t1        DOUBLE PRECISION NOT NULL,
    t2        DOUBLE PRECISION NULL
);

-- Convert to hypertable on the time column
SELECT create_hypertable('measurements', 'time', if_not_exists => TRUE);

-- Helpful index for querying by sensor and time
CREATE INDEX IF NOT EXISTS idx_measurements_sensor_time
    ON measurements (sensor_id, time DESC);
