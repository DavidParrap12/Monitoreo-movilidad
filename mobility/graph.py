"""Aggregate directed zone graph, calculate scores and optional Neo4j import."""

import argparse
import csv
import os
import sys
from collections import defaultdict
from pathlib import Path

import networkx as nx
from mobility.events import trip_events


def build_graph(events, progress=None):
    counts = defaultdict(lambda: [0, 0.0])
    for processed, event in enumerate(events, start=1):
        pair = (event["origin_zone"], event["destination_zone"])
        counts[pair][0] += 1
        counts[pair][1] += event["duration_s"]
        if progress and processed % 100000 == 0:
            progress(processed)
    graph = nx.DiGraph()
    for (origin, destination), (count, total_s) in counts.items():
        graph.add_edge(origin, destination, trips=count, mean_minutes=total_s / count / 60)
    return graph


def rankings(graph):
    rank = nx.pagerank(graph, weight="trips")
    between = nx.betweenness_centrality(graph, weight="mean_minutes", normalized=True)
    return {node: (rank[node], between[node]) for node in graph}


def write_outputs(graph, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    scores = rankings(graph)
    with (directory / "zones.csv").open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["zone_id", "pagerank", "betweenness"])
        for zone, (rank, between) in sorted(scores.items(), key=lambda x: x[1][0], reverse=True):
            writer.writerow([zone, rank, between])
    with (directory / "routes.csv").open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["origin_zone", "destination_zone", "trips", "mean_minutes"])
        for origin, destination, data in graph.edges(data=True):
            writer.writerow([origin, destination, data["trips"], data["mean_minutes"]])
    return scores


def load_neo4j(graph, scores):
    from neo4j import GraphDatabase
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")
    if not password:
        raise ValueError("Set NEO4J_PASSWORD before loading Neo4j")
    with GraphDatabase.driver(uri, auth=(user, password)) as driver:
        driver.verify_connectivity()
        driver.execute_query("CREATE CONSTRAINT zone_id IF NOT EXISTS FOR (z:Zone) REQUIRE z.id IS UNIQUE")
        driver.execute_query("MATCH (z:Zone) DETACH DELETE z")
        nodes = [{"id": int(zone), "pagerank": rank, "betweenness": between}
                 for zone, (rank, between) in scores.items()]
        driver.execute_query("UNWIND $rows AS row CREATE (z:Zone {id: row.id, pagerank: row.pagerank, betweenness: row.betweenness})", rows=nodes)
        edges = [{"origin": int(u), "destination": int(v), "trips": data["trips"],
                  "mean_minutes": data["mean_minutes"]} for u, v, data in graph.edges(data=True)]
        for start in range(0, len(edges), 1000):
            driver.execute_query("""
                UNWIND $rows AS row
                MATCH (a:Zone {id: row.origin}), (b:Zone {id: row.destination})
                CREATE (a)-[:ROUTE {trips: row.trips, mean_minutes: row.mean_minutes}]->(b)
            """, rows=edges[start:start + 1000])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="nyc_taxi_500k.csv")
    parser.add_argument("--output", default="output/graph")
    parser.add_argument("--origin", type=int)
    parser.add_argument("--destination", type=int)
    parser.add_argument("--load-neo4j", action="store_true")
    args = parser.parse_args()
    print("Leyendo viajes del CSV...", flush=True)
    graph = build_graph(trip_events(args.input),
                        progress=lambda count: print(f"{count:,} viajes válidos leídos", flush=True))
    print(f"Grafo: {graph.number_of_nodes()} zonas, {graph.number_of_edges()} rutas. Calculando centralidad...", flush=True)
    scores = write_outputs(graph, args.output)
    print("Top PageRank:", sorted(scores.items(), key=lambda x: x[1][0], reverse=True)[:5])
    print("Top betweenness:", sorted(scores.items(), key=lambda x: x[1][1], reverse=True)[:5])
    if args.origin is not None and args.destination is not None:
        try:
            route = nx.shortest_path(graph, args.origin, args.destination, weight="mean_minutes")
            print("Shortest-time zone path:", route)
            print("Estimated minutes:", nx.path_weight(graph, route, "mean_minutes"))
        except (nx.NetworkXNoPath, nx.NodeNotFound) as error:
            print(error)
    if args.load_neo4j:
        load_neo4j(graph, scores)
        print("Loaded graph into Neo4j")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Análisis interrumpido por el usuario.", file=sys.stderr)
        raise SystemExit(130)
