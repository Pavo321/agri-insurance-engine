-- Spatial index on farm polygons (GIST for fast ST_Intersects queries)
CREATE INDEX IF NOT EXISTS farms_polygon_gist
    ON farms USING GIST (polygon);

-- Spatial index on farm centroids (faster for point-in-polygon lookups)
CREATE INDEX IF NOT EXISTS farms_centroid_gist
    ON farms USING GIST (centroid);

-- B-tree index for state-level pre-filtering before spatial queries
CREATE INDEX IF NOT EXISTS farms_state_code_idx
    ON farms (state_code);

-- Index for farmer lookups by phone (admin use)
CREATE INDEX IF NOT EXISTS farmers_phone_idx
    ON farmers (phone);

-- Index for payout deduplication lookups
CREATE INDEX IF NOT EXISTS payout_records_idempotency_key_idx
    ON payout_records (idempotency_key);

-- Composite index for cooldown check: farm + rule + recent date
CREATE INDEX IF NOT EXISTS payout_records_cooldown_idx
    ON payout_records (farm_id, rule_id, created_at DESC);

-- Index for sensor readings per station (time-range queries)
CREATE INDEX IF NOT EXISTS sensor_readings_station_time_idx
    ON sensor_readings (station_id, timestamp DESC);
