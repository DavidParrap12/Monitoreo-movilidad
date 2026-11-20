"""Write canonical trip events to Parquet, optionally upload to S3."""

import argparse
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq
from mobility.events import trip_events


def export(input_path, output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    writer = None
    count = 0
    batch = []
    try:
        for event in trip_events(input_path):
            batch.append(event)
            if len(batch) == 10000:
                table = pa.Table.from_pylist(batch)
                if writer is None:
                    writer = pq.ParquetWriter(output_path, table.schema, compression="zstd")
                writer.write_table(table)
                count += len(batch)
                batch.clear()
        if batch:
            table = pa.Table.from_pylist(batch)
            if writer is None:
                writer = pq.ParquetWriter(output_path, table.schema, compression="zstd")
            writer.write_table(table)
            count += len(batch)
    finally:
        if writer:
            writer.close()
    if count == 0:
        raise ValueError("No valid trips found")
    return count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="nyc_taxi_500k.csv")
    parser.add_argument("--output", default="output/history/trips.parquet")
    parser.add_argument("--s3-bucket", help="Optional destination bucket")
    parser.add_argument("--s3-key", default="mobility/nyc-taxi-2023/trips.parquet")
    args = parser.parse_args()
    count = export(args.input, args.output)
    print(f"Exported {count} trips to {args.output}")
    if args.s3_bucket:
        import boto3
        boto3.client("s3").upload_file(args.output, args.s3_bucket, args.s3_key)
        print(f"Uploaded to s3://{args.s3_bucket}/{args.s3_key}")


if __name__ == "__main__":
    main()
