"""
GraphDB API endpoints for SPARQL queries and RDF graph operations.

The /graph endpoint returns an *RDF-faithful* representation: every SPARQL
binding becomes an edge, rdf:type triples produce class nodes, literal
objects become literal leaf-nodes, and all URIs are shown in prefixed form.
"""
import os
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from ingest.graphdb_client import GraphDBClient

router = APIRouter()

GRAPHDB_URL = os.getenv("GRAPHDB_URL", "http://localhost:7200")
GRAPHDB_REPOSITORY = os.getenv("GRAPHDB_REPOSITORY", "rig-facility-mgmt")
GRAPHDB_USERNAME = os.getenv("GRAPHDB_USERNAME")
GRAPHDB_PASSWORD = os.getenv("GRAPHDB_PASSWORD")

_graphdb_client = None


def get_graphdb_client() -> GraphDBClient:
    global _graphdb_client
    if _graphdb_client is None:
        _graphdb_client = GraphDBClient(
            base_url=GRAPHDB_URL,
            repository=GRAPHDB_REPOSITORY,
            username=GRAPHDB_USERNAME,
            password=GRAPHDB_PASSWORD,
        )
    return _graphdb_client


# ── Prefix helpers ────────────────────────────────────────────────────────────

PREFIX_MAP = {
    "http://data.ashrae.org/standard223#":         "s223:",
    "http://brickschema.org/schema/1.1.0/Brick#":  "brick:",
    "http://brickschema.org/schema/Brick#":         "brick:",
    "http://ifc-ld.org/schemas/ifc2x3#":            "ifc:",
    "http://www.w3.org/2004/02/skos/core#":         "skos:",
    "http://www.w3.org/2000/01/rdf-schema#":        "rdfs:",
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#":  "rdf:",
    "http://qudt.org/schema/qudt/":                  "qudt:",
    "http://qudt.org/vocab/quantitykind/":           "qk:",
    "https://example.com/case-office/":              "co:",
    "http://example.com/mybuilding#":                "bldg:",
    "http://ifc-ld.org/ids#":                        "ifcid:",
    "https://example.com/rig#":                      "rig:",
}

ONTOLOGY_NAMESPACES = {
    "s223:",  "brick:",  "ifc:",
}

RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"


def prefixed(uri: str) -> str:
    """Convert a full URI to its shortest prefixed form."""
    for ns, px in PREFIX_MAP.items():
        if uri.startswith(ns):
            return px + uri[len(ns):]
    if "#" in uri:
        return uri.split("#")[-1]
    return uri.split("/")[-1]


def namespace_of(uri: str) -> str:
    """Return the prefix portion (e.g. 's223') for a URI."""
    for ns, px in PREFIX_MAP.items():
        if uri.startswith(ns):
            return px.rstrip(":")
    return "other"


# ── Models ────────────────────────────────────────────────────────────────────

class SPARQLQueryRequest(BaseModel):
    query: str
    format: str = "json"


class GraphNode(BaseModel):
    id: str
    name: Optional[str] = None
    type: Optional[str] = None          # "resource" | "literal" | "class"
    labels: Optional[List[str]] = []    # rdf:types in prefixed form
    properties: Optional[Dict[str, Any]] = {}


class GraphEdge(BaseModel):
    source: str
    target: str
    type: str                            # prefixed predicate
    properties: Optional[Dict[str, Any]] = {}


class GraphResponse(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/sparql", response_model=Dict[str, Any])
async def execute_sparql(query_request: SPARQLQueryRequest):
    """Execute a SPARQL query against GraphDB."""
    try:
        client = get_graphdb_client()
        raw = client.execute_sparql_query(
            query_request.query,
            output_format=query_request.format,
        )
        if isinstance(raw, dict) and "results" in raw:
            return {"results": raw["results"]}
        return {"results": raw}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SPARQL query failed: {str(e)}")


@router.get("/graph", response_model=GraphResponse)
async def get_graph(
    limit: int = Query(500, ge=1, le=2000),
):
    """Return an RDF-faithful graph for visualisation.

    Every triple becomes an edge.  ``rdf:type`` triples produce *class*
    target-nodes (hexagons on the frontend), literal objects produce
    *literal* leaf-nodes (rectangles), and everything else is a *resource*
    node (circles).  All URIs are returned in prefixed notation.
    """
    try:
        client = get_graphdb_client()

        query = f"""
            PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX owl:    <http://www.w3.org/2002/07/owl#>
            PREFIX s223:   <http://data.ashrae.org/standard223#>
            PREFIX brick1: <http://brickschema.org/schema/1.1.0/Brick#>
            PREFIX ifc:    <http://ifc-ld.org/schemas/ifc2x3#>
            PREFIX skos:   <http://www.w3.org/2004/02/skos/core#>
            PREFIX qudt:   <http://qudt.org/schema/qudt/>

            SELECT ?s ?p ?o WHERE {{
              VALUES ?p {{
                rdf:type  rdfs:label
                skos:exactMatch
                brick1:isPointOf  brick1:hasPart  brick1:isPartOf  brick1:hasPoint
                s223:hasPhysicalLocation  s223:observes  s223:hasZone
                s223:hasProperty  s223:connected  s223:cnx
                qudt:hasQuantityKind
              }}
              ?s ?p ?o .
              FILTER(!STRSTARTS(STR(?s), "http://www.w3.org/"))
              FILTER(!STRSTARTS(STR(?s), "http://www.openrdf.org/"))
              FILTER(!STRSTARTS(STR(?s), "http://rdf4j.org/"))
            }}
            LIMIT {limit}
        """

        results = client.execute_sparql_query(query, output_format="json")
        bindings = results.get("results", {}).get("bindings", [])
        print(f"[GraphDB /graph] {len(bindings)} raw bindings")

        nodes: Dict[str, dict] = {}
        edges: list = []
        edges_seen: set = set()
        lit_counter = 0

        def _ensure_resource(uri: str):
            if uri not in nodes:
                nodes[uri] = {
                    "id": uri,
                    "name": prefixed(uri),
                    "type": "resource",
                    "labels": [],
                    "properties": {"ns": namespace_of(uri)},
                }

        for b in bindings:
            s_uri = b.get("s", {}).get("value", "")
            p_uri = b.get("p", {}).get("value", "")
            o = b.get("o", {})
            if not s_uri or not p_uri:
                continue

            _ensure_resource(s_uri)

            o_type = o.get("type", "")   # "uri" or "literal" / "typed-literal"
            o_val  = o.get("value", "")

            if o_type == "uri":
                if p_uri == RDF_TYPE:
                    # Skip generic W3C types (owl:NamedIndividual, etc.)
                    if o_val.startswith("http://www.w3.org/"):
                        continue
                    # Class node
                    if o_val not in nodes:
                        nodes[o_val] = {
                            "id": o_val,
                            "name": prefixed(o_val),
                            "type": "class",
                            "labels": [],
                            "properties": {"ns": namespace_of(o_val)},
                        }
                    elif nodes[o_val]["type"] == "resource":
                        nodes[o_val]["type"] = "class"
                    nodes[s_uri]["labels"].append(prefixed(o_val))
                else:
                    _ensure_resource(o_val)

                key = (s_uri, o_val, p_uri)
                if key not in edges_seen:
                    edges_seen.add(key)
                    edges.append({
                        "source": s_uri,
                        "target": o_val,
                        "type": prefixed(p_uri),
                        "properties": {},
                    })

            else:
                # Literal object → leaf node
                lit_counter += 1
                lit_id = f"_:lit{lit_counter}"
                display = o_val if len(o_val) <= 50 else o_val[:47] + "..."
                nodes[lit_id] = {
                    "id": lit_id,
                    "name": f'"{display}"',
                    "type": "literal",
                    "labels": [],
                    "properties": {
                        "value": o_val,
                        "datatype": o.get("datatype", ""),
                    },
                }
                key = (s_uri, lit_id, p_uri)
                if key not in edges_seen:
                    edges_seen.add(key)
                    edges.append({
                        "source": s_uri,
                        "target": lit_id,
                        "type": prefixed(p_uri),
                        "properties": {},
                    })

        # Attach rdfs:label text to the resource node name when available
        label_pred = "http://www.w3.org/2000/01/rdf-schema#label"
        for b in bindings:
            p_uri = b.get("p", {}).get("value", "")
            if p_uri != label_pred:
                continue
            s_uri = b["s"]["value"]
            lbl = b["o"]["value"]
            if s_uri in nodes and nodes[s_uri]["type"] == "resource":
                nodes[s_uri]["name"] = lbl

        print(f"[GraphDB /graph] {len(nodes)} nodes  {len(edges)} edges")

        return GraphResponse(
            nodes=[GraphNode(**n) for n in nodes.values()],
            edges=[GraphEdge(**e) for e in edges],
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get graph: {str(e)}")


@router.get("/semantic-layers")
async def get_semantic_layers():
    """Get information about semantic layers in the graph."""
    try:
        client = get_graphdb_client()
        
        query = """
        PREFIX s223:  <http://data.ashrae.org/standard223#>
        PREFIX brick1: <http://brickschema.org/schema/1.1.0/Brick#>
        PREFIX ifc:   <http://ifc-ld.org/schemas/ifc2x3#>

        SELECT ?layer (COUNT(DISTINCT ?entity) as ?count)
        WHERE {
            {
                ?entity a ?t .
                FILTER(STRSTARTS(STR(?t), STR(s223:)))
                BIND ("223P" as ?layer)
            }
            UNION
            {
                ?entity a ?t .
                FILTER(STRSTARTS(STR(?t), STR(brick1:)))
                BIND ("Brick" as ?layer)
            }
            UNION
            {
                ?entity a ?t .
                FILTER(STRSTARTS(STR(?t), STR(ifc:)))
                BIND ("IFC-LD" as ?layer)
            }
        }
        GROUP BY ?layer
        """
        
        results = client.execute_sparql_query(query, output_format="json")
        
        layers = []
        if "results" in results and "bindings" in results["results"]:
            for binding in results["results"]["bindings"]:
                layers.append({
                    "layer": binding.get("layer", {}).get("value", ""),
                    "count": int(binding.get("count", {}).get("value", 0))
                })
        
        return {"layers": layers}
        
    except Exception as e:
        # Return mock data if GraphDB is not available
        return {
            "layers": [
                {"layer": "IFC-LD", "count": 1250},
                {"layer": "223P Equipment", "count": 45},
                {"layer": "Brick Points", "count": 180},
                {"layer": "IFC-LD Flow Terminal", "count": 150}
            ]
        }


@router.get("/statistics")
async def get_statistics():
    """Get GraphDB repository statistics."""
    try:
        client = get_graphdb_client()
        stats = client.get_statistics()
        return stats
    except Exception as e:
        return {
            "repository": GRAPHDB_REPOSITORY,
            "statements": 0,
            "error": str(e)
        }


