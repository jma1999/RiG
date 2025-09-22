# rag/answer.py
import os, json, sys
from typing import List, Dict, Any, Set
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()
URI  = os.getenv("NEO4J_URI", "bolt://localhost:7687")
USER = os.getenv("NEO4J_USER", "neo4j")
PASS = os.getenv("NEO4J_PASSWORD", "changeme123")
DB   = os.getenv("NEO4J_DATABASE", "neo4j")

EVIDENCE_PATH = "data/processed/evidence.json"

def labels_has(lbls: List[str], needle: str) -> bool:
    return any(l == needle or l.endswith(":" + needle) or l == needle for l in lbls)

def main():
    # Load evidence
    try:
        ev: Dict[str, Any] = json.loads(open(EVIDENCE_PATH, "r", encoding="utf-8").read())
    except FileNotFoundError:
        print("No evidence file found. Run: python rag/query.py \"your question\" first.")
        sys.exit(1)

    nodes = ev.get("nodes", [])
    edges = ev.get("edges", [])

    # Prefer terminals already in evidence
    term_ids: Set[str] = set()
    for n in nodes:
        ntype  = (n.get("type") or "").strip()
        lbls   = n.get("labels") or []
        if ntype == "IfcFlowTerminal" or "IfcFlowTerminal" in lbls:
            if n.get("id"):
                term_ids.add(n["id"])

    # If none, try to infer by traversing FEEDS from upstream devices present in evidence
    upstream_ids: List[str] = []
    if not term_ids:
        for n in nodes:
            t = (n.get("type") or "")
            if t in ("IfcEnergyConversionDevice", "IfcFlowController", "IfcFlowSegment"):
                if n.get("id"):
                    upstream_ids.append(n["id"])

    drv = GraphDatabase.driver(URI, auth=(USER, PASS))
    with drv.session(database=DB) as s:
        if not term_ids and upstream_ids:
            # Find downstream terminals up to 6 hops from any upstream seed
            recs = s.run("""
                UNWIND $seeds AS sid
                MATCH (src {globalId:sid})
                MATCH (src)-[:FEEDS|CONNECTED_TO*1..6]->(t:IfcFlowTerminal)
                RETURN DISTINCT t.globalId AS id
            """, seeds=upstream_ids)
            for r in recs:
                term_ids.add(r["id"])

        # Fetch names + rooms + storeys for the terminals
        terms = []
        rooms_set: Set[str] = set()
        storeys_set: Set[str] = set()

        if term_ids:
            recs = s.run("""
                UNWIND $ids AS id
                MATCH (t {globalId:id})
                OPTIONAL MATCH (t)-[:IN_SPACE]->(sp:IfcSpace)
                OPTIONAL MATCH (t)-[:IN_STOREY]->(st:IfcBuildingStorey)
                RETURN id, coalesce(t.name,'') AS name,
                       collect(DISTINCT sp.name) AS rooms,
                       collect(DISTINCT st.name) AS storeys
            """, ids=list(term_ids))

            for r in recs:
                terms.append((r["name"], r["id"]))
                for x in r["rooms"] or []:
                    if x: rooms_set.add(x)
                for x in r["storeys"] or []:
                    if x: storeys_set.add(x)

    drv.close()

    # Pretty print
    if terms:
        terms_sorted = sorted(terms, key=lambda x: (x[0] or "", x[1]))
        print("Terminals downstream:")
        for name, gid in terms_sorted:
            print(f"  • {name}  [{gid}]")
    else:
        print("Terminals downstream: (none found in evidence or via FEEDS traversal)")

    rooms = sorted(rooms_set)
    storeys = sorted(storeys_set)

    if rooms:
        print("Rooms:", ", ".join(rooms))
    else:
        print("Rooms: (none – this model likely has no IfcSpace)")

    if storeys:
        print("Storeys:", ", ".join(storeys))
    else:
        print("Storeys: (none)")

if __name__ == "__main__":
    main()
