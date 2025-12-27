-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Base table for measurements
CREATE TABLE IF NOT EXISTS measurements (
    time      TIMESTAMPTZ      NOT NULL,
    sensor_id TEXT             NOT NULL,
    t1        DOUBLE PRECISION NULL,        -- temperature 1 (°C)
    t2        DOUBLE PRECISION NULL,        -- temperature 2 (°C)
    h         DOUBLE PRECISION NULL,        -- air humidity (%)
    r         DOUBLE PRECISION NULL,        -- rainfall (total mm)
    rf        INTEGER          NULL,        -- rain flip count (number of flips)
    rr        DOUBLE PRECISION NULL         -- amount of water per flip (mm)
);

-- Convert to hypertable on the time column
SELECT create_hypertable('measurements', 'time', if_not_exists => TRUE);

-- Single unique index to enforce no duplicates and support queries
CREATE UNIQUE INDEX IF NOT EXISTS idx_measurements_sensor_time
    ON measurements (sensor_id, time DESC);
