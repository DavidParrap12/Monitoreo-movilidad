CREATE KEYSPACE IF NOT EXISTS mobility
WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};

-- A 15-minute bucket and 8 shards cap partition growth for busy routes.
CREATE TABLE IF NOT EXISTS mobility.trip_events (
    route_id text,
    bucket_start timestamp,
    shard int,
    event_time timestamp,
    trip_id text,
    origin_zone int,
    destination_zone int,
    duration_s int,
    distance_km double,
    speed_kmh double,
    PRIMARY KEY ((route_id, bucket_start, shard), event_time, trip_id)
) WITH CLUSTERING ORDER BY (event_time DESC, trip_id ASC);

-- Five-minute windows contain one row per route and remain bounded by day.
CREATE TABLE IF NOT EXISTS mobility.route_windows (
    route_id text,
    event_date date,
    window_start timestamp,
    trip_count bigint,
    mean_duration_s double,
    mean_speed_kmh double,
    slow_share double,
    PRIMARY KEY ((route_id, event_date), window_start)
) WITH CLUSTERING ORDER BY (window_start DESC);
