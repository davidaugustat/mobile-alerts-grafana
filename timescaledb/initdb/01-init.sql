-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Base table for measurements
CREATE TABLE IF NOT EXISTS measurements (
    time      TIMESTAMPTZ      NOT NULL,
    sensor_id TEXT             NOT NULL,
    t1        DOUBLE PRECISION NULL,
    t2        DOUBLE PRECISION NULL,
    h         DOUBLE PRECISION NULL
);

-- Convert to hypertable on the time column
SELECT create_hypertable('measurements', 'time', if_not_exists => TRUE);

-- Single unique index to enforce no duplicates and support queries
CREATE UNIQUE INDEX IF NOT EXISTS idx_measurements_sensor_time
    ON measurements (sensor_id, time DESC);

-- Add humidity column if table already exists but lacks it
ALTER TABLE measurements ADD COLUMN IF NOT EXISTS h DOUBLE PRECISION NULL;
