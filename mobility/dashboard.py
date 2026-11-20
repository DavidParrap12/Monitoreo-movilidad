"""Build an offline HTML dashboard from the graph CSV exports."""

import argparse
import csv
import json
from pathlib import Path


TEMPLATE = Path(__file__).with_name("dashboard.html")


def read_graph(directory):
    with (directory / "zones.csv").open(newline="", encoding="utf-8") as file:
        zones = [
            {
                "id": int(row["zone_id"]),
                "pagerank": float(row["pagerank"]),
                "betweenness": float(row["betweenness"]),
            }
            for row in csv.DictReader(file)
        ]
    with (directory / "routes.csv").open(newline="", encoding="utf-8") as file:
        routes = [
            {
                "origin": int(row["origin_zone"]),
                "destination": int(row["destination_zone"]),
                "trips": int(row["trips"]),
                "minutes": float(row["mean_minutes"]),
            }
            for row in csv.DictReader(file)
        ]
    return zones, routes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("output/graph"),
                        help="Directory containing zones.csv and routes.csv")
    parser.add_argument("--output", type=Path, default=None,
                        help="HTML destination (default: INPUT/index.html)")
    args = parser.parse_args()
    zones, routes = read_graph(args.input)
    destination = args.output or args.input / "index.html"
    # Escape '<' so CSV data can never close the embedded script element.
    data = json.dumps({"zones": zones, "routes": routes}, separators=(",", ":")).replace("<", "\\u003c")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(TEMPLATE.read_text(encoding="utf-8").replace("/* GRAPH_DATA */ null", data),
                           encoding="utf-8")
    print(f"Dashboard creado: {destination.resolve()} ({len(zones)} zonas, {len(routes)} rutas)")


if __name__ == "__main__":
    main()
