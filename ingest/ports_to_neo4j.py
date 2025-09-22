# ingest/ports_to_neo4j.py
import os
import ifcopenshell
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()
URI  = os.getenv("NEO4J_URI", "bolt://localhost:7687")
USER = os.getenv("NEO4J_USER", "neo4j")
PASS = os.getenv("NEO4J_PASSWORD", "changeme123")
DB   = os.getenv("NEO4J_DATABASE", "neo4j")

IFC = "data/raw/ifc/sample_house/20210125Prova.ifc"

def gid(x):
    return getattr(x, "GlobalId", None)

def sval(x):
    # convert enum/typed to plain string
    try:
        return str(x) if x is not None else None
    except Exception:
        return None

def main():
    f = ifcopenshell.open(IFC)

    # --- 1) Create/merge ALL ports as nodes ---
    ports = f.by_type("IfcDistributionPort")
    port_info = {}
    for p in ports:
        pg = gid(p)
        if not pg:
            continue
        port_info[pg] = {
            "type": p.is_a(),
            "name": getattr(p, "Name", None) or "",
            "flow": sval(getattr(p, "FlowDirection", None)),      # IFC2x3/IFC4
            "ptype": sval(getattr(p, "PredefinedType", None))     # may be None
        }

    drv = GraphDatabase.driver(URI, auth=(USER, PASS))
    created_ports = 0
    with drv.session(database=DB) as s:
        for pg, meta in port_info.items():
            s.run("""
                MERGE (p:IfcDistributionPort {globalId:$id})
                ON CREATE SET p.type=$type, p.name=$name, p.flow=$flow, p.predef=$ptype
                ON MATCH  SET p.type=coalesce(p.type,$type),
                               p.name=coalesce(p.name,$name),
                               p.flow=coalesce(p.flow,$flow),
                               p.predef=coalesce(p.predef,$ptype)
            """, id=pg, **meta)
            created_ports += 1

    # --- 2) Attach ports to host elements ---
    host_pairs = set()

    # 2a) IfcRelConnectsPortToElement
    for r in f.by_type("IfcRelConnectsPortToElement"):
        p = getattr(r, "RelatingPort", None) or getattr(r, "RelatedPort", None)
        e = getattr(r, "RelatedElement", None) or getattr(r, "RelatingElement", None)
        if p and e and gid(p) and gid(e):
            host_pairs.add((gid(e), gid(p)))

    # 2b) IfcRelNests (some authoring tools nest ports under elements)
    for r in f.by_type("IfcRelNests"):
        rel = getattr(r, "RelatingObject", None)
        ros = getattr(r, "RelatedObjects", []) or []
        if rel and ros:
            eg = gid(rel)
            if not eg:
                continue
            for obj in ros:
                if obj.is_a("IfcDistributionPort") and gid(obj):
                    host_pairs.add((eg, gid(obj)))

    with drv.session(database=DB) as s:
        for eg, pg in host_pairs:
            s.run("""
                MATCH (e {globalId:$eg}), (p:IfcDistributionPort {globalId:$pg})
                MERGE (e)-[:HAS_PORT]->(p)
            """, eg=eg, pg=pg)

    # --- 3) Port-to-port connectivity ---
    pp_links = set()
    for r in f.by_type("IfcRelConnectsPorts"):
        a = getattr(r, "RelatingPort", None)
        b = getattr(r, "RelatedPort", None)
        if a and b and gid(a) and gid(b):
            pp_links.add((gid(a), gid(b)))

    with drv.session(database=DB) as s:
        for a, b in pp_links:
            s.run("""
                MATCH (pa:IfcDistributionPort {globalId:$a}),
                      (pb:IfcDistributionPort {globalId:$b})
                MERGE (pa)-[:CONNECTED_TO]->(pb)
            """, a=a, b=b)

    # --- 4) Element-level connectivity + FEEDS where direction implies it ---
    with drv.session(database=DB) as s:
        for a, b in pp_links:
            s.run("""
                MATCH (pa:IfcDistributionPort {globalId:$a})<-[:HAS_PORT]-(ea),
                      (pb:IfcDistributionPort {globalId:$b})<-[:HAS_PORT]-(eb)
                WITH pa, pb, ea, eb
                MERGE (ea)-[:CONNECTED_TO]->(eb)
            """, a=a, b=b)

        # FEEDS: SOURCE -> SINK
        for a, b in pp_links:
            s.run("""
                MATCH (pa:IfcDistributionPort {globalId:$a})<-[:HAS_PORT]-(ea),
                      (pb:IfcDistributionPort {globalId:$b})<-[:HAS_PORT]-(eb)
                WHERE toUpper(coalesce(pa.flow,'')) = 'SOURCE'
                  AND toUpper(coalesce(pb.flow,'')) = 'SINK'
                MERGE (ea)-[:FEEDS]->(eb)
            """, a=a, b=b)

    drv.close()
    print(f"Ports created/merged: {created_ports}")
    print(f"Ports attached to hosts: {len(host_pairs)}")
    print(f"Port links (CONNECTED_TO): {len(pp_links)}")
    print("Derived element CONNECTED_TO edges created (count equals port links where both hosts exist).")
    print("Derived FEEDS edges created where FlowDirection SOURCE→SINK was available.")

if __name__ == "__main__":
    main()
