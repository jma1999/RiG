# ingest/ifcjson_to_neo4j.py
import os, sys, json, pathlib
import argparse
from typing import Any, Dict, Iterable, List, Optional
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Neo4j connection settings from environment variables or defaults
URI  = os.getenv("NEO4J_URI", "bolt://localhost:7687")
USER = os.getenv("NEO4J_USER", "neo4j")
PASS = os.getenv("NEO4J_PASSWORD", "changeme123")
DB   = os.getenv("NEO4J_DATABASE", "neo4j")

# Spatial types
SPATIAL_TYPES = {
    "IfcProject","IfcSite","IfcBuilding","IfcBuildingStorey","IfcSpace"
}
# Types considered terminals for quick counting / tagging
TERMINAL_TYPES = {"IfcFlowTerminal", "IfcDistributionTerminal", "IfcDuctTerminal"}

# Super-simple helper to map IFC type → a coarse CMMS-ish class
def cmms_label(ifc_type: str) -> str:
    if ifc_type in SPATIAL_TYPES:
        return ifc_type
    if ifc_type.startswith("IfcSystem"):
        return "IfcSystem"
    if ifc_type.startswith("IfcFlow") or ifc_type.startswith("IfcDistribution"):
        return "IfcDistributionElement"
    if ifc_type.startswith("IfcElement"):
        return "IfcElement"
    return ifc_type  # fallback

# Helper function to extract reference ID
def ref_id(x: Any) -> Optional[str]:
    if x is None:
        return None
    if isinstance(x, str):
        return x
    if isinstance(x, dict):
        return x.get("ref") or x.get("id") or x.get("GlobalId") or x.get("globalId")
    if isinstance(x, list) and x:
        # some ifcJSON pack singletons as 1-element arrays
        return ref_id(x[0])
    return None

# Helper function to extract name
def get_name(obj: Dict) -> str:
    for k in ("Name","LongName","name","Longname","ObjectName"):
        v = obj.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    # sometimes in "attributes"
    attrs = obj.get("attributes") or {}
    for k in ("Name","LongName","name"):
        v = attrs.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""

# Helper function to extract type
def get_type(obj: Dict) -> str:
    for k in ("type","class","ifcType"):
        v = obj.get(k)
        if isinstance(v, str) and v:
            return v
    # some exporters pack under "schema"/"spec"; fall back
    return obj.get("schema") or "Unknown"

# Helper function to extract property sets
def extract_psets(obj: Dict) -> Dict[str, Any]:
    """
    Normalizes property sets when available.
    Looks in common places: 'psets', 'Properties', 'HasPropertySets', 'attributes.PropertySets'
    Produces flat dict like {'Pset_Manufacturer': 'Acme', 'InstallYear': 2016}
    """
    out: Dict[str, Any] = {}
    # direct maps
    for key in ("psets","Properties","properties","property_sets"):
        p = obj.get(key)
        if isinstance(p, dict):
            for k, v in p.items():
                if isinstance(v, dict) and "NominalValue" in v:
                    out[k] = v.get("NominalValue")
                else:
                    out[k] = v
    # list-of-sets shape
    candidates: List[Dict[str, Any]] = []
    for k in ("HasPropertySets","PropertySets"):
        v = obj.get(k)
        if isinstance(v, list):
            candidates.extend(v)
    attrs = obj.get("attributes") or {}
    for k in ("HasPropertySets","PropertySets"):
        v = attrs.get(k)
        if isinstance(v, list):
            candidates.extend(v)
    for ps in candidates:
        pname = ps.get("Name") or ps.get("name")
        props = ps.get("HasProperties") or ps.get("Properties") or []
        if isinstance(props, list):
            for p in props:
                n = p.get("Name") or p.get("name")
                val = p.get("NominalValue") or p.get("Value") or p.get("nominalValue")
                if pname and n:
                    out[f"{pname}.{n}"] = val
                elif n:
                    out[n] = val

    # keep only JSON-serializable scalars
    clean: Dict[str, Any] = {}
    for k, v in out.items():
        if isinstance(v, (str, int, float, bool)) or v is None:
            clean[k] = v
        else:
            clean[k] = str(v)
    return clean

# Select and flatten relevant property set fields
def select_flat_props(ps: dict) -> dict:
    """
    Pick a few commonly useful pset fields and turn them into real properties.
    Extend this list as you learn your model.
    """
    keep_keys = [
        "Pset_Manufacturer.Manufacturer",
        "Pset_Manufacturer.ModelReference",
        "Pset_Asset.SerialNumber",
        "Pset_Asset.InstallationDate",
        "InstallYear",
        "Pset_MemberCommon.Span",
        "Pset_MemberCommon.IsExternal",
        "Pset_MemberCommon.Reference",
        "Pset_MemberCommon.LoadBearing",
    ]
    out = {}
    for k in keep_keys:
        if k in ps:
            sk = k.replace(".", "_").replace(" ", "_")
            out[sk] = ps.get(k)
    return out

# Helper function to load instances from ifcJSON
def load_instances(data: Dict) -> Dict[str, Dict]:
    # Accept several ifcJSON variants:
    #  - {"objects": {"GUID": {...}}}
    #  - {"instances": {"GUID": {...}}}
    #  - {"objects": [...]} (list)
    #  - top-level list: [{...}, {...}]
    #  - {"GUID": {...}}  (flat mapping)
    for key in ("objects", "instances"):
        v = data.get(key)
        if isinstance(v, dict):
            return v
        if isinstance(v, list):
            out: Dict[str, Dict] = {}
            for obj in v:
                if not isinstance(obj, dict):
                    continue
                gid = ref_id(obj) or obj.get("globalId") or obj.get("GlobalId")
                if gid:
                    out[gid] = obj
            if out:
                return out

    # top-level list variant
    if isinstance(data, list):
        out: Dict[str, Dict] = {}
        for obj in data:
            if not isinstance(obj, dict):
                continue
            gid = ref_id(obj) or obj.get("globalId") or obj.get("GlobalId")
            if gid:
                out[gid] = obj
        if out:
            return out

    # some exporters wrap instances under a top-level 'data' list/dict
    if isinstance(data, dict) and 'data' in data:
        inner = data['data']
        # if inner is a dict mapping GUID->obj
        if isinstance(inner, dict):
            return inner
        # if inner is a list of objects
        if isinstance(inner, list):
            out: Dict[str, Dict] = {}
            for obj in inner:
                if not isinstance(obj, dict):
                    continue
                gid = ref_id(obj) or obj.get('globalId') or obj.get('GlobalId')
                if gid:
                    out[gid] = obj
            if out:
                return out

    # fallback: if file is just a GUID->obj map
    if isinstance(data, dict) and all(isinstance(v, dict) for v in data.values()):
        return data  # flat GUID -> obj map

    raise ValueError("Unsupported ifcJSON structure; expected 'objects'/'instances' mapping or a list of instances")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path", help="Path to ifcJSON file")
    parser.add_argument("--source", default=None, help="Logical source tag, e.g., Arch/Mech")
    parser.add_argument("--batch-size", type=int, default=1000, help="Batch size for Neo4j writes")
    args = parser.parse_args()

    path = pathlib.Path(args.path)
    source = args.source or path.stem
    batch_size = args.batch_size

    data = json.loads(path.read_text())
    inst = load_instances(data)

    driver = GraphDatabase.driver(URI, auth=(USER, PASS))
    created = 0

    # Start Neo4j session
    with driver.session(database=DB) as s:
        # Create constraints and indexes for performance
        print("🔧 Setting up constraints and indexes...")
        try:
            s.run("CREATE CONSTRAINT IF NOT EXISTS FOR (n:IfcEntity) REQUIRE n.globalId IS UNIQUE")
            s.run("CREATE INDEX IF NOT EXISTS FOR (n:IfcEntity) ON (n.type)")
            s.run("CREATE INDEX IF NOT EXISTS FOR (n:IfcEntity) ON (n.source)")
            s.run("CREATE INDEX IF NOT EXISTS FOR (n:IfcEntity) ON (n.name)")
        except Exception as e:
            print(f"⚠️  Constraint/index creation failed (may already exist): {e}")

        # Pass 1: create nodes in batches
        print(f"📦 Creating nodes in batches of {batch_size}...")
        node_batches = []
        for guid, obj in inst.items():
            if not isinstance(obj, dict):
                continue
            ifc_type = get_type(obj)
            name = get_name(obj)
            psets = extract_psets(obj)
            psets_json = json.dumps(psets, ensure_ascii=False)
            props_flat = select_flat_props(psets)

            # Every node has :IfcEntity and its IFC type as a label
            label = cmms_label(ifc_type)

            # Attributes and flow direction
            attrs = obj.get("attributes") or {}
            attrs_json = json.dumps(attrs, ensure_ascii=False)
            flow_dir = attrs.get("FlowDirection") or obj.get("FlowDirection")

            node_batches.append({
                "id": guid,
                "name": name,
                "ifc_type": ifc_type,
                "source": source,
                "psets_json": psets_json,
                "attrs_json": attrs_json,
                "flow_dir": flow_dir,
                "props_flat": props_flat,
                "labels": [ifc_type, label] + (["TERMINAL"] if ifc_type in TERMINAL_TYPES else [])
            })

            if len(node_batches) >= batch_size:
                _batch_create_nodes(s, node_batches)
                created += len(node_batches)
                node_batches = []

        # Process remaining nodes
        if node_batches:
            _batch_create_nodes(s, node_batches)
            created += len(node_batches)

        # Pass 2: relationships in batches
        print("🔗 Creating relationships in batches...")
        rel_batches = []
        for guid, obj in inst.items():
            if not isinstance(obj, dict):
                continue
            t = get_type(obj)
            if not t.startswith("IfcRel"):
                continue

            # Common field names across exporters:
            rs = obj.get("RelatingStructure") or obj.get("relatingStructure")
            re = obj.get("RelatedElements") or obj.get("relatedElements")
            ro = obj.get("RelatedObjects")  or obj.get("relatedObjects")
            rb = obj.get("RelatedBuildings") or obj.get("relatedBuildings")
            rg = obj.get("RelatingGroup") or obj.get("relatingGroup")
            rso = obj.get("RelatingObject") or obj.get("relatingObject")

            # Check for specific relationship types
            if t == "IfcRelContainedInSpatialStructure" and rs and re:
                parent = ref_id(rs)
                kids = re if isinstance(re, list) else [re]
                for k in kids:
                    child = ref_id(k)
                    if parent and child:
                        rel_batches.append({"type": "CONTAINS", "parent": parent, "child": child})
            
            elif t == "IfcRelAggregates" and rso and ro:
                parent = ref_id(rso)
                kids = ro if isinstance(ro, list) else [ro]
                for k in kids:
                    child = ref_id(k)
                    if parent and child:
                        rel_batches.append({"type": "AGGREGATES", "parent": parent, "child": child})

            elif t == "IfcRelServicesBuildings" and rb:
                sys_ref = ref_id(obj.get("RelatingSystem") or obj.get("relatingSystem"))
                blds = rb if isinstance(rb, list) else [rb]
                for b in blds:
                    bld = ref_id(b)
                    if sys_ref and bld:
                        rel_batches.append({"type": "SERVICES", "parent": sys_ref, "child": bld})

            elif t == "IfcRelAssignsToGroup" and rg and ro:
                sys_ref = ref_id(rg)
                objs = ro if isinstance(ro, list) else [ro]
                for o in objs:
                    el = ref_id(o)
                    if sys_ref and el:
                        rel_batches.append({"type": "ASSIGNED_TO_SYSTEM", "parent": el, "child": sys_ref})
            
            elif t == "IfcRelConnectsPortToElement":
                rp = obj.get("RelatingPort") or obj.get("relatingPort")
                re = obj.get("RelatedElement") or obj.get("relatedElement")
                port = ref_id(rp); elem = ref_id(re)
                if port and elem:
                    rel_batches.append({"type": "HAS_PORT", "parent": elem, "child": port})

            elif t == "IfcRelConnectsPorts":
                pa = ref_id(obj.get("RelatingPort") or obj.get("relatingPort"))
                pb = ref_id(obj.get("RelatedPort")  or obj.get("relatedPort"))
                if pa and pb:
                    rel_batches.append({"type": "PORT_CONNECTED_TO", "parent": pa, "child": pb})

            elif t == "IfcRelConnectsElements":
                a = ref_id(obj.get("RelatingElement") or obj.get("relatingElement"))
                b = ref_id(obj.get("RelatedElement")  or obj.get("relatedElement"))
                if a and b:
                    rel_batches.append({"type": "CONNECTED_TO", "parent": a, "child": b})

            # Process batches when they get large
            if len(rel_batches) >= batch_size:
                _batch_create_relationships(s, rel_batches)
                rel_batches = []

        # Process remaining relationships
        if rel_batches:
            _batch_create_relationships(s, rel_batches)

        # Post-processing: derive connections from ports (run once)
        print("🔧 Deriving connections from ports...")
        s.run("""
        MATCH (e1)-[:HAS_PORT]->(p1:IfcDistributionPort)-[:PORT_CONNECTED_TO]->(p2:IfcDistributionPort)<-[:HAS_PORT]-(e2)
        MERGE (e1)-[:CONNECTED_TO]->(e2)
        """)

        # Directed FEEDS when port directions are available (run once)
        s.run("""
        MATCH (src)-[:HAS_PORT]->(p:IfcDistributionPort)-[:PORT_CONNECTED_TO]->(q:IfcDistributionPort)<-[:HAS_PORT]-(dst)
        WHERE toUpper(coalesce(p.flowDirection,'')) CONTAINS 'SOURCE'
        AND toUpper(coalesce(q.flowDirection,'')) CONTAINS 'SINK'
        MERGE (src)-[:FEEDS]->(dst)
        """)

    # Close Neo4j driver
    driver.close()
    print(f"✅ Loaded nodes from %s. Created/merged: %d" % (path.name, created))
    print("✅ Relationships merged: CONTAINS / AGGREGATES / SERVICES / ASSIGNED_TO_SYSTEM (when present)")


def _batch_create_nodes(session, node_batches):
    """Create nodes in batch using UNWIND for better performance"""
    session.run("""
    UNWIND $batches AS batch
    MERGE (n:IfcEntity {globalId: batch.id})
    ON CREATE SET
        n.name = batch.name,
        n.type = batch.ifc_type,
        n.source = batch.source,
        n.psets_json = batch.psets_json,
        n.attrs_json = batch.attrs_json,
        n.flowDirection = coalesce(batch.flow_dir, n.flowDirection)
    ON MATCH SET
        n.name = coalesce(n.name, batch.name),
        n.type = batch.ifc_type,
        n.source = coalesce(n.source, batch.source),
        n.psets_json = coalesce(n.psets_json, batch.psets_json),
        n.attrs_json = coalesce(n.attrs_json, batch.attrs_json),
        n.flowDirection = coalesce(n.flowDirection, batch.flow_dir)
    SET n += batch.props_flat
    """, batches=node_batches)
    
    # Add labels in separate batch
    session.run("""
    UNWIND $batches AS batch
    MATCH (n:IfcEntity {globalId: batch.id})
    CALL apoc.create.addLabels(n, batch.labels) YIELD node
    RETURN count(node)
    """, batches=node_batches)


def _batch_create_relationships(session, rel_batches):
    """Create relationships in batch using UNWIND for better performance"""
    session.run("""
    UNWIND $batches AS batch
    MATCH (a:IfcEntity {globalId: batch.parent}), (b:IfcEntity {globalId: batch.child})
    MERGE (a)-[r]->(b)
    SET r.type = batch.type
    """, batches=rel_batches)
    
if __name__ == "__main__":
    main()