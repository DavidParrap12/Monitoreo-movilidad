"""Convert NYC taxi trips into stable, replayable zone-to-zone events."""

import csv
import hashlib
from datetime import datetime
from pathlib import Path


def trip_events(path: str | Path):
    with open(path, encoding="utf-8-sig", newline="") as source:
        for line_number, row in enumerate(csv.DictReader(source), start=2):
            try:
                origin = int(row["pulocationid"])
                destination = int(row["dolocationid"])
                pickup = datetime.fromisoformat(row["tpep_pickup_datetime"])
                dropoff = datetime.fromisoformat(row["tpep_dropoff_datetime"])
                distance_km = float(row["trip_distance"]) * 1.609344
                duration_s = int((dropoff - pickup).total_seconds())
                if pickup.year != 2023 or dropoff.year != 2023:
                    continue
                # TLC IDs 264 (Unknown) and 265 (Outside NYC) are not city zones.
                if not (1 <= origin <= 263 and 1 <= destination <= 263):
                    continue
                if not (60 <= duration_s <= 4 * 3600 and 0 < distance_km <= 200):
                    continue
                speed_kmh = distance_km / duration_s * 3600
                if speed_kmh > 130:
                    continue
                trip_id = hashlib.sha256(f"{line_number}:{row}".encode()).hexdigest()[:24]
                yield {
                    "trip_id": trip_id,
                    "route_id": f"{origin}:{destination}",
                    "origin_zone": origin,
                    "destination_zone": destination,
                    "event_time": pickup.isoformat(timespec="seconds"),
                    "duration_s": duration_s,
                    "distance_km": round(distance_km, 4),
                    "speed_kmh": round(speed_kmh, 4),
                }
            except (ValueError, TypeError, KeyError, OverflowError):
                continue


def bucket_and_shard(event):
    timestamp = datetime.fromisoformat(event["event_time"])
    minute = (timestamp.minute // 15) * 15
    bucket = timestamp.replace(minute=minute, second=0, microsecond=0)
    return bucket.isoformat(timespec="seconds"), int(event["trip_id"][:8], 16) % 8
