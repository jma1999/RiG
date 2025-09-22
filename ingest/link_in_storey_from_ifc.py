# ingest/link_in_storey_from_ifc.py
import os, ifcopenshell
from neo4j import GraphDatabase
from dotenv import load_dotenv
load_dotenv()

URI=os.getenv("NEO4J_URI","bolt://localhost:7687")
USER=os.getenv("NEO4J_USER","neo4j")
PASS=os.getenv("NEO4J_PASSWORD","changeme123")
DB=os.getenv("NEO4J_DATABASE","neo4j")

IFC="data/raw/ifc/sample_house/20210125Prova.ifc"

f = ifcopenshell.open(IFC)
rels = f.by_type("IfcRelContainedInSpatialStructure")

pairs = []  # (elem_gid, storey_gid)
for r in rels:
    rs = r.RelatingStructure
    if not rs or rs.is_a() != "IfcBuildingStorey":
        continue
    st_gid = rs.GlobalId
    for e in r.RelatedElements or []:
        gid = getattr(e, "GlobalId", None)
        if gid: pairs.append((gid, st_gid))

drv = GraphDatabase.driver(URI, auth=(USER,PASS))
with drv.session(database=DB) as s:
    for eg, sg in pairs:
        s.run("""
            MATCH (e {globalId:$eg}), (st:IfcBuildingStorey {globalId:$sg})
            MERGE (e)-[:IN_STOREY]->(st)
        """, eg=eg, sg=sg)
drv.close()
print("Linked IN_STOREY:", len(pairs))
