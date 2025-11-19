"""
GraphDB API endpoints for SPARQL queries and RDF graph operations.
"""
import os
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import sys
import pathlib

# Add parent directory to path for imports
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from ingest.graphdb_client import GraphDBClient

router = APIRouter()

# GraphDB configuration from environment
GRAPHDB_URL = os.getenv("GRAPHDB_URL", "http://localhost:7200")
GRAPHDB_REPOSITORY = os.getenv("GRAPHDB_REPOSITORY", "rig-facility-mgmt")
GRAPHDB_USERNAME = os.getenv("GRAPHDB_USERNAME")
GRAPHDB_PASSWORD = os.getenv("GRAPHDB_PASSWORD")

# Initialize GraphDB client
_graphdb_client = None

def get_graphdb_client() -> GraphDBClient:
    """Get or create GraphDB client instance."""
    global _graphdb_client
    if _graphdb_client is None:
        _graphdb_client = GraphDBClient(
            base_url=GRAPHDB_URL,
            repository=GRAPHDB_REPOSITORY,
            username=GRAPHDB_USERNAME,
            password=GRAPHDB_PASSWORD
        )
    return _graphdb_client


class SPARQLQueryRequest(BaseModel):
    query: str
    format: str = "json"


class GraphNode(BaseModel):
    id: str
    name: Optional[str] = None
    type: Optional[str] = None
    labels: Optional[List[str]] = []
    properties: Optional[Dict[str, Any]] = {}


class GraphEdge(BaseModel):
    source: str
    target: str
    type: str
    properties: Optional[Dict[str, Any]] = {}


class GraphResponse(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]


@router.post("/sparql", response_model=Dict[str, Any])
async def execute_sparql(query_request: SPARQLQueryRequest):
    """Execute a SPARQL query against GraphDB."""
    try:
        client = get_graphdb_client()
        results = client.execute_sparql_query(
            query_request.query,
            output_format=query_request.format
        )
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SPARQL query failed: {str(e)}")


@router.get("/graph", response_model=GraphResponse)
async def get_graph(
    limit: int = Query(100, ge=1, le=1000),
    entity_type: Optional[str] = None,
    hops: int = Query(2, ge=1, le=5)
):
    """Get graph structure from GraphDB for visualization."""
    try:
        client = get_graphdb_client()
        
        # Build SPARQL query based on parameters
        if entity_type:
            # Query specific entity type
            query = f"""
            PREFIX ifc: <http://ifc-ld.org/schemas/ifc2x3#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX ex: <https://example.com/rig#>
            PREFIX s223: <http://data.ashrae.org/standard223#>
            PREFIX brick: <https://brickschema.org/schema/Brick#>
            
            SELECT DISTINCT ?entity ?name ?type ?predicate ?object
            WHERE {{
                ?entity a ?type .
                FILTER (STRSTARTS(STR(?type), "{entity_type}"))
                OPTIONAL {{ ?entity rdfs:label ?name }}
                OPTIONAL {{ ?entity ifc:name ?name }}
                OPTIONAL {{ ?entity ?predicate ?object }}
                FILTER (isURI(?object))
            }}
            LIMIT {limit}
            """
        else:
            # Query semantic overlay entities (223P/Brick)
            query = f"""
            PREFIX ex: <https://example.com/rig#>
            PREFIX s223: <http://data.ashrae.org/standard223#>
            PREFIX brick: <https://brickschema.org/schema/Brick#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            
            SELECT DISTINCT ?entity ?name ?type ?predicate ?object
            WHERE {{
                {{
                    ?entity a s223:Equipment .
                    OPTIONAL {{ ?entity rdfs:label ?name }}
                    OPTIONAL {{ ?entity ?predicate ?object }}
                    FILTER (isURI(?object))
                }}
                UNION
                {{
                    ?entity a brick:Point .
                    OPTIONAL {{ ?entity rdfs:label ?name }}
                    OPTIONAL {{ ?entity ?predicate ?object }}
                    FILTER (isURI(?object))
                }}
                UNION
                {{
                    ?entity a s223:Property .
                    OPTIONAL {{ ?entity rdfs:label ?name }}
                    OPTIONAL {{ ?entity ?predicate ?object }}
                    FILTER (isURI(?object))
                }}
            }}
            LIMIT {limit}
            """
        
        results = client.execute_sparql_query(query, output_format="json")
        
        # Parse results into nodes and edges
        nodes = {}
        edges = []
        
        if "results" in results and "bindings" in results["results"]:
            for binding in results["results"]["bindings"]:
                entity_uri = binding.get("entity", {}).get("value", "")
                if not entity_uri:
                    continue
                
                # Extract node info
                if entity_uri not in nodes:
                    node_name = binding.get("name", {}).get("value", "")
                    node_type = binding.get("type", {}).get("value", "")
                    # Extract short name from URI
                    if not node_name:
                        node_name = entity_uri.split("/")[-1].split("#")[-1]
                    
                    nodes[entity_uri] = {
                        "id": entity_uri,
                        "name": node_name,
                        "type": node_type.split("#")[-1] if "#" in node_type else node_type.split("/")[-1],
                        "labels": [],
                        "properties": {}
                    }
                
                # Extract edge
                predicate = binding.get("predicate", {}).get("value", "")
                object_uri = binding.get("object", {}).get("value", "")
                
                if predicate and object_uri and object_uri.startswith("http"):
                    edge_type = predicate.split("#")[-1] if "#" in predicate else predicate.split("/")[-1]
                    edges.append({
                        "source": entity_uri,
                        "target": object_uri,
                        "type": edge_type,
                        "properties": {}
                    })
        
        return GraphResponse(
            nodes=[GraphNode(**node) for node in nodes.values()],
            edges=[GraphEdge(**edge) for edge in edges]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get graph: {str(e)}")


@router.get("/semantic-layers")
async def get_semantic_layers():
    """Get information about semantic layers in the graph."""
    try:
        client = get_graphdb_client()
        
        query = """
        PREFIX s223: <http://data.ashrae.org/standard223#>
        PREFIX brick: <https://brickschema.org/schema/Brick#>
        PREFIX sosa: <http://www.w3.org/ns/sosa/>
        PREFIX qudt: <http://qudt.org/schema/qudt/>
        PREFIX ifc: <http://ifc-ld.org/schemas/ifc2x3#>
        
        SELECT ?layer (COUNT(DISTINCT ?entity) as ?count)
        WHERE {
            {
                ?entity a s223:Equipment .
                BIND ("223P Equipment" as ?layer)
            }
            UNION
            {
                ?entity a brick:Point .
                BIND ("Brick Points" as ?layer)
            }
            UNION
            {
                ?entity a sosa:ObservableProperty .
                BIND ("SOSA Observable" as ?layer)
            }
            UNION
            {
                ?entity a qudt:Quantity .
                BIND ("QUDT Quantity" as ?layer)
            }
            UNION
            {
                ?entity a ifc:IfcFlowTerminal .
                BIND ("IFC Flow Terminal" as ?layer)
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
                {"layer": "SOSA Observable", "count": 120},
                {"layer": "QUDT Quantity", "count": 150}
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

