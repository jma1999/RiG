#!/usr/bin/env python3
"""
Run evaluation queries over the IFC-derived RDF graph and optional telemetry DB.

Outputs:
  - data/processed/eval_metrics.json
  - docs/eval_metrics.md
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Any, List, Tuple

from rdflib import Graph, Namespace, URIRef

try:
    import psycopg2
except Exception:
    psycopg2 = None


BASE_DIR = Path(__file__).resolve().parent.parent
RDF_FILE = BASE_DIR / "data/processed/rdf/20210125Prova_reduced.ttl"
SEMANTIC_OVERLAY = BASE_DIR / "data/semantic/ft_136276_semantic.ttl"
OUT_JSON = BASE_DIR / "data/processed/eval_metrics.json"
OUT_MD = BASE_DIR / "docs/eval_metrics.md"


IFC_LD = Namespace("http://ifc-ld.org/schemas/")  # Coverage: ifc2x3# and ifc4#
IFC_LD_SCHEMA = Namespace("http://ifc-ld.org/schemas/ifc2x3#")  # IFC entity queries
BRICK = Namespace("https://brickschema.org/schema/Brick#")
S223 = Namespace("http://data.ashrae.org/standard223#")


def load_graph() -> Graph:
    graph = Graph()
    graph.parse(str(RDF_FILE), format="turtle")
    if SEMANTIC_OVERLAY.exists():
        graph.parse(str(SEMANTIC_OVERLAY), format="turtle")
    return graph


def run_select(graph: Graph, query: str) -> List[Dict[str, Any]]:
    results = []
    for row in graph.query(query):
        row_dict = {}
        for idx, var in enumerate(row.labels):
            row_dict[str(var)] = row[idx]
        results.append(row_dict)
    return results


def namespace_coverage(rows: List[Dict[str, Any]]) -> Dict[str, bool]:
    """Check coverage of Brick, 223P, IFC-LD (no ifcOWL, SOSA, QUDT)."""
    namespaces = {
        "IFC-LD": str(IFC_LD),
        "Brick": str(BRICK),
        "ASHRAE223P": str(S223),
    }
    coverage = {k: False for k in namespaces}
    for row in rows:
        for value in row.values():
            if isinstance(value, URIRef):
                value_str = str(value)
                for label, ns in namespaces.items():
                    if value_str.startswith(ns):
                        coverage[label] = True
    return coverage


def expand_neighborhood(graph: Graph, seeds: List[URIRef], hops: int = 2, max_seeds: int = 5) -> int:
    """Count unique triples within N hops of seed URIs."""
    seen_triples = set()
    frontier = set(seeds[:max_seeds])
    visited = set(frontier)

    for _ in range(hops):
        next_frontier = set()
        for node in frontier:
            for triple in graph.triples((node, None, None)):
                seen_triples.add(triple)
                if isinstance(triple[2], URIRef) and triple[2] not in visited:
                    next_frontier.add(triple[2])
            for triple in graph.triples((None, None, node)):
                seen_triples.add(triple)
                if isinstance(triple[0], URIRef) and triple[0] not in visited:
                    next_frontier.add(triple[0])
        visited |= next_frontier
        frontier = next_frontier

    return len(seen_triples)


def get_timescale_connection():
    if psycopg2 is None:
        raise RuntimeError("psycopg2 not installed")

    host = os.getenv("TIMESCALEDB_HOST", "localhost")
    port = int(os.getenv("TIMESCALEDB_PORT", "5432"))
    dbname = os.getenv("TIMESCALEDB_DB", "rig_timeseries")
    user = os.getenv("TIMESCALEDB_USER", "rig_user")
    password = os.getenv("TIMESCALEDB_PASSWORD", "rig_password")

    return psycopg2.connect(
        host=host, port=port, dbname=dbname, user=user, password=password
    )


def try_timescale_query() -> Dict[str, Any]:
    try:
        conn = get_timescale_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM telemetry_sample WHERE point_id = %s",
            ("ft_136276_sat",),
        )
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        return {"available": True, "row_count": int(count)}
    except Exception as e:
        return {"available": False, "error": str(e)}


def main() -> None:
    if not RDF_FILE.exists():
        raise FileNotFoundError(f"Missing RDF file: {RDF_FILE}")

    graph = load_graph()
    total_triples = len(graph)

    queries = [
        # Spatial
        {
            "type": "Spatial",
            "name": "Count IfcSpace",
            "query": f"SELECT (COUNT(?s) AS ?count) WHERE {{ ?s a <{IFC_LD_SCHEMA}IfcSpace> . }}",
            "seed_query": f"SELECT ?s WHERE {{ ?s a <{IFC_LD_SCHEMA}IfcSpace> . }} LIMIT 10",
            "schemas": ["IFC-LD"],
        },
        {
            "type": "Spatial",
            "name": "Count IfcBuildingStorey",
            "query": f"SELECT (COUNT(?s) AS ?count) WHERE {{ ?s a <{IFC_LD_SCHEMA}IfcBuildingStorey> . }}",
            "seed_query": f"SELECT ?s WHERE {{ ?s a <{IFC_LD_SCHEMA}IfcBuildingStorey> . }} LIMIT 10",
            "schemas": ["IFC-LD"],
        },
        {
            "type": "Spatial",
            "name": "Count IfcDoor",
            "query": f"SELECT (COUNT(?s) AS ?count) WHERE {{ ?s a <{IFC_LD_SCHEMA}IfcDoor> . }}",
            "seed_query": f"SELECT ?s WHERE {{ ?s a <{IFC_LD_SCHEMA}IfcDoor> . }} LIMIT 10",
            "schemas": ["IFC-LD"],
        },
        {
            "type": "Spatial",
            "name": "Count IfcWindow",
            "query": f"SELECT (COUNT(?s) AS ?count) WHERE {{ ?s a <{IFC_LD_SCHEMA}IfcWindow> . }}",
            "seed_query": f"SELECT ?s WHERE {{ ?s a <{IFC_LD_SCHEMA}IfcWindow> . }} LIMIT 10",
            "schemas": ["IFC-LD"],
        },
        {
            "type": "Spatial",
            "name": "List IfcSpace (sample)",
            "query": f"SELECT ?s WHERE {{ ?s a <{IFC_LD_SCHEMA}IfcSpace> . }} LIMIT 10",
            "schemas": ["IFC-LD"],
        },
        # System-level
        {
            "type": "System",
            "name": "Count IfcFlowTerminal",
            "query": f"SELECT (COUNT(?s) AS ?count) WHERE {{ ?s a <{IFC_LD_SCHEMA}IfcFlowTerminal> . }}",
            "seed_query": f"SELECT ?s WHERE {{ ?s a <{IFC_LD_SCHEMA}IfcFlowTerminal> . }} LIMIT 10",
            "schemas": ["IFC-LD"],
        },
        {
            "type": "System",
            "name": "Count IfcEnergyConversionDevice",
            "query": f"SELECT (COUNT(?s) AS ?count) WHERE {{ ?s a <{IFC_LD_SCHEMA}IfcEnergyConversionDevice> . }}",
            "seed_query": f"SELECT ?s WHERE {{ ?s a <{IFC_LD_SCHEMA}IfcEnergyConversionDevice> . }} LIMIT 10",
            "schemas": ["IFC-LD"],
        },
        {
            "type": "System",
            "name": "Count IfcFlowSegment",
            "query": f"SELECT (COUNT(?s) AS ?count) WHERE {{ ?s a <{IFC_LD_SCHEMA}IfcFlowSegment> . }}",
            "seed_query": f"SELECT ?s WHERE {{ ?s a <{IFC_LD_SCHEMA}IfcFlowSegment> . }} LIMIT 10",
            "schemas": ["IFC-LD"],
        },
        {
            "type": "System",
            "name": "Count IfcDistributionElement",
            "query": f"SELECT (COUNT(?s) AS ?count) WHERE {{ ?s a <{IFC_LD_SCHEMA}IfcDistributionElement> . }}",
            "seed_query": f"SELECT ?s WHERE {{ ?s a <{IFC_LD_SCHEMA}IfcDistributionElement> . }} LIMIT 10",
            "schemas": ["IFC-LD"],
        },
        {
            "type": "System",
            "name": "Count IfcSystem",
            "query": f"SELECT (COUNT(?s) AS ?count) WHERE {{ ?s a <{IFC_LD_SCHEMA}IfcSystem> . }}",
            "seed_query": f"SELECT ?s WHERE {{ ?s a <{IFC_LD_SCHEMA}IfcSystem> . }} LIMIT 10",
            "schemas": ["IFC-LD"],
        },
        # Cross-domain (requires semantic overlay)
        {
            "type": "Cross-domain",
            "name": "Brick+223P points",
            "query": f"""
                SELECT DISTINCT ?p WHERE {{
                    ?p a <{S223}Property> .
                    ?p a ?brickType .
                    FILTER(STRSTARTS(STR(?brickType), "{BRICK}"))
                }} LIMIT 50
            """,
            "schemas": ["Brick", "ASHRAE223P"],
        },
        {
            "type": "Cross-domain",
            "name": "Brick sensors (SAT)",
            "query": f"""
                SELECT ?p WHERE {{
                    ?p a <{BRICK}Supply_Air_Temperature_Sensor> .
                }} LIMIT 50
            """,
            "schemas": ["Brick"],
        },
        {
            "type": "Cross-domain",
            "name": "223P equipment",
            "query": f"""
                SELECT ?e WHERE {{
                    ?e a <{S223}Equipment> .
                }} LIMIT 50
            """,
            "schemas": ["ASHRAE223P"],
        },
    ]

    results = []
    for q in queries:
        rows = run_select(graph, q["query"])

        count_value = None
        if rows and "count" in rows[0]:
            try:
                count_value = int(rows[0]["count"])
            except Exception:
                count_value = None

        if count_value is not None:
            nonempty = count_value > 0
        else:
            nonempty = len(rows) > 0

        # Use first few URIs as seeds for neighborhood size
        seeds = []
        seed_rows = rows
        if "seed_query" in q:
            seed_rows = run_select(graph, q["seed_query"])
        for row in seed_rows:
            for val in row.values():
                if isinstance(val, URIRef):
                    seeds.append(val)
        neighborhood_triples = expand_neighborhood(graph, seeds, hops=2) if seeds else 0

        results.append(
            {
                "type": q["type"],
                "name": q["name"],
                "rows": len(rows),
                "count_value": count_value,
                "nonempty": nonempty,
                "schemas_used": q.get("schemas", []),
                "neighborhood_triples_2hop": neighborhood_triples,
            }
        )

    # Aggregate metrics (RDF only for neighborhood stats)
    total_queries = len(results)
    nonempty_queries = sum(1 for r in results if r["nonempty"])
    correctness_pct = round(100 * nonempty_queries / total_queries, 2) if total_queries else 0.0
    avg_triples = (
        round(
            sum(r["neighborhood_triples_2hop"] for r in results) / total_queries, 2
        )
        if total_queries
        else 0.0
    )

    # Coverage by category (will be recomputed after temporal queries)
    category_counts = {}

    # TimescaleDB availability + temporal queries
    timescale = try_timescale_query()

    temporal_results = []
    if timescale.get("available"):
        conn = get_timescale_connection()
        cur = conn.cursor()

        temporal_queries = [
            {
                "type": "Temporal",
                "name": "Count SAT rows (last 60 min)",
                "sql": """
                    SELECT COUNT(*) FROM telemetry_sample
                    WHERE point_id = %s AND time >= NOW() - INTERVAL '60 minutes'
                """,
                "params": ("ft_136276_sat",),
                "value_key": "count",
            },
            {
                "type": "Temporal",
                "name": "Latest SAT value",
                "sql": """
                    SELECT value FROM telemetry_sample
                    WHERE point_id = %s
                    ORDER BY time DESC
                    LIMIT 1
                """,
                "params": ("ft_136276_sat",),
                "value_key": "value",
            },
            {
                "type": "Temporal",
                "name": "Avg SAT value (last 60 min)",
                "sql": """
                    SELECT AVG(value) FROM telemetry_sample
                    WHERE point_id = %s AND time >= NOW() - INTERVAL '60 minutes'
                """,
                "params": ("ft_136276_sat",),
                "value_key": "avg",
            },
            {
                "type": "Temporal",
                "name": "Min/Max SAT value (last 60 min)",
                "sql": """
                    SELECT MIN(value), MAX(value) FROM telemetry_sample
                    WHERE point_id = %s AND time >= NOW() - INTERVAL '60 minutes'
                """,
                "params": ("ft_136276_sat",),
                "value_key": "minmax",
            },
            {
                "type": "Temporal",
                "name": "15-min buckets SAT (last 60 min)",
                "sql": """
                    SELECT time_bucket('15 minutes', time) as bucket, AVG(value)
                    FROM telemetry_sample
                    WHERE point_id = %s AND time >= NOW() - INTERVAL '60 minutes'
                    GROUP BY bucket
                    ORDER BY bucket
                """,
                "params": ("ft_136276_sat",),
                "value_key": "buckets",
            },
        ]

        for tq in temporal_queries:
            cur.execute(tq["sql"], tq["params"])
            rows = cur.fetchall()

            nonempty = False
            if tq["value_key"] == "count":
                count_value = int(rows[0][0]) if rows else 0
                nonempty = count_value > 0
                value = count_value
            elif tq["value_key"] == "value":
                value = float(rows[0][0]) if rows and rows[0][0] is not None else None
                nonempty = value is not None
            elif tq["value_key"] == "avg":
                value = float(rows[0][0]) if rows and rows[0][0] is not None else None
                nonempty = value is not None
            elif tq["value_key"] == "minmax":
                value = (
                    (float(rows[0][0]) if rows and rows[0][0] is not None else None),
                    (float(rows[0][1]) if rows and rows[0][1] is not None else None),
                )
                nonempty = value[0] is not None or value[1] is not None
            else:
                value = len(rows)
                nonempty = value > 0

            temporal_results.append(
                {
                    "type": tq["type"],
                    "name": tq["name"],
                    "rows": len(rows),
                    "value": value,
                    "nonempty": nonempty,
                    "schemas_used": ["TimescaleDB"],
                    "neighborhood_triples_2hop": 0,
                }
            )

        cur.close()
        conn.close()
    else:
        # Temporal queries unavailable
        temporal_results = [
            {
                "type": "Temporal",
                "name": "TimescaleDB unavailable",
                "rows": 0,
                "value": None,
                "nonempty": False,
                "schemas_used": ["TimescaleDB"],
                "neighborhood_triples_2hop": 0,
            }
        ]

    all_results = results + temporal_results

    # Coverage by category (include temporal)
    category_counts = {}
    for r in all_results:
        category_counts.setdefault(r["type"], {"total": 0, "nonempty": 0})
        category_counts[r["type"]]["total"] += 1
        if r["nonempty"]:
            category_counts[r["type"]]["nonempty"] += 1

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "rdf_file": str(RDF_FILE),
        "semantic_overlay": str(SEMANTIC_OVERLAY),
        "triples_total": total_triples,
        "total_queries": len(all_results),
        "nonempty_queries": sum(1 for r in all_results if r["nonempty"]),
        "correctness_pct": round(
            100 * sum(1 for r in all_results if r["nonempty"]) / len(all_results), 2
        )
        if all_results
        else 0.0,
        "avg_neighborhood_triples_2hop": avg_triples,
        "category_coverage": category_counts,
        "timescale": timescale,
        "results": all_results,
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    # Markdown summary
    lines = [
        "# Evaluation Metrics (Generated)",
        "",
        f"- Timestamp: `{payload['timestamp']}`",
        f"- RDF triples (combined): `{payload['triples_total']}`",
        f"- Queries executed: `{payload['total_queries']}`",
        f"- Non-empty query results: `{payload['nonempty_queries']}`",
        f"- Correctness proxy (non-empty %): `{payload['correctness_pct']}%`",
        f"- Avg. 2-hop neighborhood triples: `{payload['avg_neighborhood_triples_2hop']}`",
        "",
        "## Coverage by Category",
        "",
        "| Category | Non-empty / Total |",
        "|---|---|",
    ]
    for cat, counts in payload["category_coverage"].items():
        lines.append(f"| {cat} | {counts['nonempty']} / {counts['total']} |")

    lines += [
        "",
        "## TimescaleDB Availability",
        "",
        f"- Available: `{payload['timescale'].get('available')}`",
    ]
    if payload["timescale"].get("available"):
        lines.append(f"- Rows for `ft_136276_sat`: `{payload['timescale'].get('row_count')}`")
    else:
        lines.append(f"- Error: `{payload['timescale'].get('error')}`")

    lines += [
        "",
        "## Per-Query Summary",
        "",
        "| Type | Query | Rows | Count/Value | Non-empty | 2-hop Triples | Schemas |",
        "|---|---|---:|---:|:---:|---:|---|",
    ]
    for r in payload["results"]:
        value_cell = "-"
        if "count_value" in r and r["count_value"] is not None:
            value_cell = str(r["count_value"])
        elif "value" in r and r["value"] is not None:
            value_cell = str(r["value"])
        lines.append(
            f"| {r['type']} | {r['name']} | {r['rows']} | {value_cell} | {'Yes' if r['nonempty'] else 'No'} | {r['neighborhood_triples_2hop']} | {', '.join(r.get('schemas_used', []))} |"
        )

    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"✅ Wrote {OUT_JSON}")
    print(f"✅ Wrote {OUT_MD}")


if __name__ == "__main__":
    main()
