# ingest/extract_coords.py
import argparse, ifcopenshell
from ifcopenshell.util.placement import get_local_placement
from neo4j import GraphDatabase
import os
from dotenv import load_dotenv
load_dotenv()

URI  = os.getenv("NEO4J_URI", "bolt://localhost:7687")
USER = os.getenv("NEO4J_USER", "neo4j")
PASS = os.getenv("NEO4J_PASSWORD", "changeme123")
DB   = os.getenv("NEO4J_DATABASE", "neo4j")

# returns (x,y,z) in model coordinates using placement matrices
def world_xyz(ent):
    try:
        m = get_local_placement(ent.ObjectPlacement)  # 4x3 matrix
        # m = [[xx,xy,xz,tx], [yx,yy,yz,ty], [zx,zy,zz,tz], [0,0,0,1]]
        tx = m[0][3]; ty = m[1][3]; tz = m[2][3]
        return float(tx), float(ty), float(tz)
    except Exception:
        # Fallback: try RelativePlacement.Location if present
        rp = getattr(ent.ObjectPlacement, "RelativePlacement", None)
        if rp and getattr(rp, "Location", None):
            p = rp.Location.Coordinates
            return float(p[0] or 0), float(p[1] or 0), float(p[2] or 0)
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ifc", help="path to IFC")
    # default: doors + duct/air terminals; extend as you like
    ap.add_argument("--types", nargs="+",
        default=["IfcDoor","IfcDuctTerminal","IfcDistributionTerminal"])
    args = ap.parse_args()

    f = ifcopenshell.open(args.ifc)
    driver = GraphDatabase.driver(URI, auth=(USER,PASS))
    updated = 0
    with driver.session(database=DB) as s:
        for t in args.types:
            try:
                ents = f.by_type(t)
            except:
                continue
            for e in ents:
                if not getattr(e, "ObjectPlacement", None):
                    continue
                xyz = world_xyz(e)
                if not xyz:
                    continue
                gid = e.GlobalId
                s.run("""
                    MATCH (n:IfcEntity {globalId:$id})
                    SET n.x=$x, n.y=$y, n.z=$z
                """, id=gid, x=xyz[0], y=xyz[1], z=xyz[2])
                updated += 1
    driver.close()
    print(f"✅ coords set on {updated} nodes")

if __name__ == "__main__":
    main()
