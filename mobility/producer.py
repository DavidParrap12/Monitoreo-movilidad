"""Replay taxi trips to Kafka; event timestamps remain their historical values."""

import argparse
import json
import time
from kafka import KafkaProducer
from mobility.events import trip_events


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="nyc_taxi_500k.csv")
    parser.add_argument("--bootstrap", default="localhost:9092")
    parser.add_argument("--topic", default="taxi-trips")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--skip", type=int, default=0, help="Skip this many valid events before publishing")
    parser.add_argument("--rate", type=float, default=0, help="Events per second; 0 is unthrottled")
    args = parser.parse_args()
    producer = KafkaProducer(bootstrap_servers=args.bootstrap, value_serializer=lambda v: json.dumps(v).encode())
    sent = 0
    try:
        for index, event in enumerate(trip_events(args.input)):
            if index < args.skip:
                continue
            producer.send(args.topic, key=event["route_id"].encode(), value=event)
            sent += 1
            if args.rate > 0:
                time.sleep(1 / args.rate)
            if args.limit and sent >= args.limit:
                break
        producer.flush()
    finally:
        producer.close()
    print(f"Published {sent} events")


if __name__ == "__main__":
    main()
