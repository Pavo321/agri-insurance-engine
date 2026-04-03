-- Convert sensor_readings to TimescaleDB hypertable (partitioned by week)
SELECT create_hypertable('sensor_readings', 'timestamp',
    chunk_time_interval => INTERVAL '1 week',
    if_not_exists => TRUE
);

-- Convert farm_daily_stats to hypertable (partitioned by month)
SELECT create_hypertable('farm_daily_stats', 'stat_date',
    chunk_time_interval => INTERVAL '1 month',
    if_not_exists => TRUE
);

-- Continuous aggregate: daily rainfall sum per station
-- Used by rules engine for 14-day rolling window (pre-computed, fast queries)
CREATE MATERIALIZED VIEW IF NOT EXISTS rainfall_daily_per_station
WITH (timescaledb.continuous) AS
    SELECT
        station_id,
        time_bucket('1 day', timestamp) AS bucket,
        SUM(rainfall_mm)   AS daily_rainfall_mm,
        AVG(temp_celsius)  AS avg_temp_c,
        AVG(humidity_pct)  AS avg_humidity_pct
    FROM sensor_readings
    GROUP BY station_id, bucket
WITH NO DATA;

-- Refresh policy: update aggregate every hour
SELECT add_continuous_aggregate_policy('rainfall_daily_per_station',
    start_offset => INTERVAL '16 days',
    end_offset   => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);
