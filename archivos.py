"""Download a reproducible slice of NYC Open Data Yellow Taxi trips."""

import argparse
import csv
import os
from pathlib import Path
import tempfile

import requests

DATASET = "https://data.cityofnewyork.us/resource/4b4i-vvec.csv"


def download(output: Path, rows: int = 530_000, page_size: int = 25_000):
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", newline="", encoding="utf-8", dir=output.parent,
        prefix=output.name + ".", suffix=".tmp", delete=False
    ) as target:
        temporary = Path(target.name)
        writer = None
        total = 0
        try:
            with requests.Session() as session:
                while total < rows:
                    limit = min(page_size, rows - total)
                    response = session.get(
                        DATASET,
                        params={"$limit": limit, "$offset": total, "$order": ":id"},
                        timeout=120,
                    )
                    response.raise_for_status()
                    source = csv.DictReader(response.text.splitlines())
                    if writer is None:
                        writer = csv.DictWriter(target, fieldnames=source.fieldnames)
                        writer.writeheader()
                    elif source.fieldnames != writer.fieldnames:
                        raise ValueError("Source columns changed during download")
                    page_count = 0
                    for row in source:
                        writer.writerow(row)
                        page_count += 1
                    if page_count != limit:
                        raise ValueError(f"Expected {limit} rows at offset {total}; got {page_count}")
                    total += page_count
                    print(f"Downloaded {total:,}/{rows:,} rows", flush=True)
            target.close()
            os.replace(temporary, output)
        except Exception:
            target.close()
            temporary.unlink(missing_ok=True)
            raise
    return total


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("nyc_taxi_500k.csv"))
    parser.add_argument("--rows", type=int, default=530_000)
    args = parser.parse_args()
    if args.rows < 500_000:
        parser.error("--rows must be at least 500000")
    download(args.output, args.rows)
