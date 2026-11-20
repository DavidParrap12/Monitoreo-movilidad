import csv
import tempfile
import unittest
from pathlib import Path
from mobility.events import bucket_and_shard, trip_events


class EventsTest(unittest.TestCase):
    def test_invalid_trips_are_skipped_and_id_is_stable(self):
        fields = ["pulocationid", "dolocationid", "tpep_pickup_datetime",
                  "tpep_dropoff_datetime", "trip_distance"]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "trips.csv"
            with path.open("w", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=fields)
                writer.writeheader()
                writer.writerow(dict(zip(fields, ["1", "2", "2023-01-01T00:03:00",
                                                   "2023-01-01T00:13:00", "2"])))
                writer.writerow(dict(zip(fields, ["1", "2", "2023-01-01T00:13:00",
                                                   "2023-01-01T00:03:00", "2"])))
                writer.writerow(dict(zip(fields, ["264", "2", "2023-01-01T00:03:00",
                                                   "2023-01-01T00:13:00", "2"])))
                writer.writerow(dict(zip(fields, ["1", "2", "2022-12-31T00:03:00",
                                                   "2022-12-31T00:13:00", "2"])))
            events = list(trip_events(path))
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["trip_id"], list(trip_events(path))[0]["trip_id"])
            self.assertEqual(events[0]["route_id"], "1:2")
            bucket, shard = bucket_and_shard(events[0])
            self.assertEqual(bucket, "2023-01-01T00:00:00")
            self.assertIn(shard, range(8))


if __name__ == "__main__":
    unittest.main()
