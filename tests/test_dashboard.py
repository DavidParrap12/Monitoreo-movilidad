import csv
import tempfile
import unittest
from pathlib import Path

from mobility.dashboard import read_graph


class DashboardTest(unittest.TestCase):
    def test_reads_graph_exports(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            with (directory / "zones.csv").open("w", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(["zone_id", "pagerank", "betweenness"])
                writer.writerow([161, 0.02, 0.01])
            with (directory / "routes.csv").open("w", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(["origin_zone", "destination_zone", "trips", "mean_minutes"])
                writer.writerow([161, 237, 5, 8.2])
            zones, routes = read_graph(directory)
            self.assertEqual(zones, [{"id": 161, "pagerank": 0.02, "betweenness": 0.01}])
            self.assertEqual(routes, [{"origin": 161, "destination": 237, "trips": 5, "minutes": 8.2}])


if __name__ == "__main__":
    unittest.main()
