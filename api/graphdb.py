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
    "http://ifc-ld.org/schemas/ifc4#":              "ifc:",
    "http://ifc-ld.org/schemas/ifc2x3#":            "ifc:",
    "http://www.w3.org/2004/02/skos/core#":         "skos:",
    "http://www.w3.org/2000/01/rdf-schema#":        "rdfs:",
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#":  "rdf:",
    "http://qudt.org/schema/qudt/":                  "qudt:",
    "http://qudt.org/vocab/quantitykind/":           "qk:",
    "https://example.com/case-office/":              "co:",
    "http://example.com/case_office#":               "co:",
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
            PREFIX ifc4:   <http://ifc-ld.org/schemas/ifc4#>
            PREFIX ifc2x3: <http://ifc-ld.org/schemas/ifc2x3#>
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
                ifc4:name  ifc2x3:name
                ifc4:longName  ifc2x3:longName
                ifc4:objectType  ifc2x3:objectType
                ifc4:tag  ifc2x3:tag
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


@router.get("/top-nodes")
async def get_top_nodes(limit: int = Query(80, ge=1, le=500)):
    """Return high-level typed entities for the graph explorer's initial view."""
    try:
        client = get_graphdb_client()

        query = f"""
            PREFIX rdfs:  <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX ifc4:  <http://ifc-ld.org/schemas/ifc4#>
            PREFIX ifc2x3:<http://ifc-ld.org/schemas/ifc2x3#>

            SELECT DISTINCT ?s ?type ?label WHERE {{
              ?s a ?type .
              OPTIONAL {{ ?s rdfs:label ?rdfsLabel }}
              OPTIONAL {{ ?s ifc4:name ?ifc4Name }}
              OPTIONAL {{ ?s ifc2x3:name ?ifc2x3Name }}
              BIND(COALESCE(?rdfsLabel, ?ifc4Name, ?ifc2x3Name) AS ?label)
              FILTER(!STRSTARTS(STR(?s), "http://www.w3.org/"))
              FILTER(!STRSTARTS(STR(?type), "http://www.w3.org/"))
              FILTER(!STRSTARTS(STR(?s), "http://www.openrdf.org/"))
              FILTER(!STRSTARTS(STR(?s), "http://rdf4j.org/"))
            }}
            LIMIT {limit}
        """

        results = client.execute_sparql_query(query, output_format="json")
        bindings = results.get("results", {}).get("bindings", [])

        seen: Dict[str, dict] = {}
        for b in bindings:
            uri = b.get("s", {}).get("value", "")
            rdf_type = b.get("type", {}).get("value", "")
            label = b.get("label", {}).get("value", "")
            if not uri:
                continue
            if uri not in seen:
                seen[uri] = {
                    "uri": uri,
                    "id": prefixed(uri),
                    "label": label or prefixed(uri),
                    "types": [prefixed(rdf_type)] if rdf_type else [],
                    "ns": namespace_of(uri),
                }
            else:
                if rdf_type:
                    px = prefixed(rdf_type)
                    if px not in seen[uri]["types"]:
                        seen[uri]["types"].append(px)
                if label and not seen[uri]["label"].startswith(label):
                    seen[uri]["label"] = label

        nodes = sorted(seen.values(), key=lambda n: n["label"])
        return {"nodes": nodes}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get top nodes: {str(e)}")


@router.get("/node-triples")
async def get_node_triples(uri: str = Query(..., description="Full URI of the subject")):
    """Return all predicate–object pairs for a given subject URI,
    structured for JSON-LD playground-style visualisation."""
    try:
        client = get_graphdb_client()

        query = f"""
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

            SELECT ?p ?o WHERE {{
              <{uri}> ?p ?o .
            }}
            LIMIT 200
        """

        results = client.execute_sparql_query(query, output_format="json")
        bindings = results.get("results", {}).get("bindings", [])

        triples = []
        for b in bindings:
            p_uri = b.get("p", {}).get("value", "")
            o = b.get("o", {})
            o_type = o.get("type", "")
            o_val = o.get("value", "")

            is_uri = o_type == "uri"
            display_val = o_val if len(o_val) <= 80 else o_val[:77] + "..."

            triples.append({
                "predicate": prefixed(p_uri),
                "predicateUri": p_uri,
                "value": prefixed(o_val) if is_uri else display_val,
                "rawValue": o_val,
                "isUri": is_uri,
                "ns": namespace_of(o_val) if is_uri else None,
            })

        label = prefixed(uri)
        for t in triples:
            if t["predicateUri"] == "http://www.w3.org/2000/01/rdf-schema#label":
                label = t["rawValue"]
                break

        return {
            "uri": uri,
            "id": prefixed(uri),
            "label": label,
            "triples": triples,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get node triples: {str(e)}")


@router.get("/semantic-layers")
async def get_semantic_layers():
    """Get information about semantic layers in the graph."""
    try:
        client = get_graphdb_client()
        
        query = """
        PREFIX s223:  <http://data.ashrae.org/standard223#>
        PREFIX brick1: <http://brickschema.org/schema/1.1.0/Brick#>

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
                FILTER(STRSTARTS(STR(?t), "http://ifc-ld.org/schemas/"))
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


@router.get("/expand")
async def expand_graph_node(
    uri: str = Query(..., description="Full URI of the node to expand"),
    limit: int = Query(80, ge=1, le=300),
):
    """Return a local RDF neighborhood around one URI for interactive expansion."""
    try:
        client = get_graphdb_client()

        query = f"""
            PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

            SELECT ?s ?p ?o WHERE {{
              {{
                BIND(<{uri}> AS ?s)
                ?s ?p ?o .
              }}
              UNION
              {{
                ?s ?p <{uri}> .
                BIND(<{uri}> AS ?o)
              }}
              FILTER(!STRSTARTS(STR(?s), "http://www.w3.org/"))
              FILTER(!STRSTARTS(STR(?s), "http://www.openrdf.org/"))
              FILTER(!STRSTARTS(STR(?s), "http://rdf4j.org/"))
            }}
            LIMIT {limit}
        """

        results = client.execute_sparql_query(query, output_format="json")
        bindings = results.get("results", {}).get("bindings", [])

        nodes: Dict[str, dict] = {}
        edges: list = []
        edges_seen: set = set()
        lit_counter = 0

        def _ensure_resource(node_uri: str):
            if node_uri not in nodes:
                nodes[node_uri] = {
                    "id": node_uri,
                    "name": prefixed(node_uri),
                    "type": "resource",
                    "labels": [],
                    "properties": {"ns": namespace_of(node_uri)},
                }

        for b in bindings:
            s_uri = b.get("s", {}).get("value", "")
            p_uri = b.get("p", {}).get("value", "")
            o = b.get("o", {})
            if not s_uri or not p_uri:
                continue

            _ensure_resource(s_uri)

            o_type = o.get("type", "")
            o_val = o.get("value", "")

            if o_type == "uri":
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
                lit_counter += 1
                lit_id = f"_:lit_expand_{lit_counter}"
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

        return {
            "center": uri,
            "nodes": list(nodes.values()),
            "edges": edges,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to expand node: {str(e)}")


@router.get("/focus")
async def get_focused_graph(
    uri: str = Query(..., description="Full URI of the center node"),
    limit: int = Query(40, ge=1, le=120),
):
    """Return a small, human-readable neighborhood around one URI."""
    try:
        client = get_graphdb_client()

        query = f"""
        PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        PREFIX brick1: <http://brickschema.org/schema/1.1.0/Brick#>
        PREFIX s223: <http://data.ashrae.org/standard223#>

        SELECT ?s ?p ?o ?oLabel
        WHERE {{
          BIND(<{uri}> AS ?s)

          ?s ?p ?o .

          OPTIONAL {{ ?o rdfs:label ?oLabel }}

          FILTER(
            ?p IN (
              rdf:type,
              rdfs:label,
              skos:exactMatch,
              brick1:hasPart,
              brick1:isPartOf,
              brick1:hasPoint,
              brick1:isPointOf,
              s223:hasPhysicalLocation,
              s223:hasProperty,
              s223:observes,
              s223:hasZone
            )
          )
        }}
        LIMIT {limit}
        """

        results = client.execute_sparql_query(query, output_format="json")
        bindings = results.get("results", {}).get("bindings", [])

        nodes: Dict[str, dict] = {}
        edges: List[dict] = []
        lit_counter = 0

        def ensure_resource(node_uri: str, fallback_name: Optional[str] = None):
            if node_uri not in nodes:
                nodes[node_uri] = {
                    "id": node_uri,
                    "label": fallback_name or prefixed(node_uri),
                    "name": fallback_name or prefixed(node_uri),
                    "type": "resource",
                    "ns": namespace_of(node_uri),
                    "properties": {},
                }

        ensure_resource(uri)

        for b in bindings:
            s_uri = b.get("s", {}).get("value", "")
            p_uri = b.get("p", {}).get("value", "")
            o = b.get("o", {})
            o_type = o.get("type", "")
            o_val = o.get("value", "")
            o_label = b.get("oLabel", {}).get("value", "")

            if not s_uri or not p_uri or not o_val:
                continue

            if o_type == "uri":
                ensure_resource(o_val, o_label or prefixed(o_val))

                # mark rdf:type objects as class nodes
                if p_uri == RDF_TYPE:
                    nodes[o_val]["type"] = "class"

                edges.append({
                    "source": s_uri,
                    "target": o_val,
                    "predicate": prefixed(p_uri),
                })
            else:
                lit_counter += 1
                lit_id = f"_:lit_focus_{lit_counter}"
                display = o_val if len(o_val) <= 50 else o_val[:47] + "..."
                nodes[lit_id] = {
                    "id": lit_id,
                    "label": display,
                    "name": display,
                    "type": "literal",
                    "ns": "other",
                    "properties": {"value": o_val},
                }
                edges.append({
                    "source": s_uri,
                    "target": lit_id,
                    "predicate": prefixed(p_uri),
                })

        # try to give center node a human-readable label
        label_query = f"""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX ifc4: <http://ifc-ld.org/schemas/ifc4#>
        PREFIX ifc2x3: <http://ifc-ld.org/schemas/ifc2x3#>

        SELECT ?label WHERE {{
          OPTIONAL {{ <{uri}> rdfs:label ?rdfsLabel }}
          OPTIONAL {{ <{uri}> ifc4:name ?ifc4Name }}
          OPTIONAL {{ <{uri}> ifc2x3:name ?ifc2x3Name }}
          BIND(COALESCE(?rdfsLabel, ?ifc4Name, ?ifc2x3Name) AS ?label)
        }}
        LIMIT 1
        """
        label_results = client.execute_sparql_query(label_query, output_format="json")
        label_bindings = label_results.get("results", {}).get("bindings", [])
        if label_bindings:
            lbl = label_bindings[0].get("label", {}).get("value")
            if lbl:
                nodes[uri]["label"] = lbl
                nodes[uri]["name"] = lbl

        return {
            "center": uri,
            "nodes": list(nodes.values()),
            "edges": edges,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get focused graph: {str(e)}")

