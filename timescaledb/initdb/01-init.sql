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

-- Table to associate sensors with rooms over time
CREATE TABLE IF NOT EXISTS room_assoc (
    sensor_id TEXT             NOT NULL,
    room_id   TEXT             NOT NULL,
    start_date TIMESTAMPTZ    NULL,
    end_date   TIMESTAMPTZ    NULL
);

-- Indexes to speed up joins/filters
CREATE INDEX IF NOT EXISTS idx_room_assoc_sensor ON room_assoc (sensor_id);
CREATE INDEX IF NOT EXISTS idx_room_assoc_room ON room_assoc (room_id);

-- View that exposes measurements per room by joining with time ranges
CREATE OR REPLACE VIEW room_measurements_view AS
SELECT
  ra.room_id,
  m.time,
  m.sensor_id,
  m.t1,
  m.t2,
  m.h,
  m.r,
  m.rf,
  m.rr
FROM room_assoc ra
JOIN measurements m
  ON m.sensor_id = ra.sensor_id
 AND m.time >= COALESCE(ra.start_date, '-infinity'::timestamptz)
 AND m.time <  COALESCE(ra.end_date,   'infinity'::timestamptz);
