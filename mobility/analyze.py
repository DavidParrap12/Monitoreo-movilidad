"""Reproducible local analyses and timing for the technical report."""

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
from time import perf_counter

from mobility.events import trip_events


def analyze(path):
    started = perf_counter()
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    with open(path, encoding="utf-8-sig", newline="") as source:
        raw_count = sum(1 for _ in csv.DictReader(source))

    hours = Counter()
    origins = Counter()
    destinations = Counter()
    route_stats = defaultdict(lambda: [0, 0.0, 0])
    valid_count = 0
    for event in trip_events(path):
        valid_count += 1
        hours[event["event_time"][11:13]] += 1
        origins[event["origin_zone"]] += 1
        destinations[event["destination_zone"]] += 1
        stats = route_stats[event["route_id"]]
        stats[0] += 1
        stats[1] += event["duration_s"]
        stats[2] += event["speed_kmh"] < 15
    routes = [
        {"route_id": key, "trips": count, "mean_minutes": round(seconds / count / 60, 2),
         "slow_share": round(slow / count, 4)}
        for key, (count, seconds, slow) in route_stats.items()
    ]
    return {
        "input": str(path), "sha256": digest.hexdigest(), "raw_records": raw_count,
        "valid_records": valid_count, "excluded_records": raw_count - valid_count,
        "valid_share": round(valid_count / raw_count, 4),
        "distinct_routes": len(route_stats),
        "analyses": {
            "peak_hours": [{"hour": k, "trips": v} for k, v in hours.most_common(5)],
            "top_origins": [{"zone": k, "trips": v} for k, v in origins.most_common(5)],
            "top_destinations": [{"zone": k, "trips": v} for k, v in destinations.most_common(5)],
            "top_routes": sorted(routes, key=lambda row: row["trips"], reverse=True)[:5],
            "slow_routes_min_30": sorted(
                (row for row in routes if row["trips"] >= 30),
                key=lambda row: (-row["slow_share"], -row["trips"]),
            )[:5],
        },
        "elapsed_seconds": round(perf_counter() - started, 3),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("nyc_taxi_500k.csv"))
    parser.add_argument("--output", type=Path, default=Path("output/analysis.json"))
    args = parser.parse_args()
    result = analyze(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
