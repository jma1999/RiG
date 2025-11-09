# rag/sparql_rag.py
"""
SPARQL-based GraphRAG for RDF Graphs.

This module provides GraphRAG functionality using SPARQL queries instead of Cypher.
It enables retrieval-augmented generation over RDF graphs stored in GraphDB.

Key features:
- Natural language to SPARQL query generation
- Semantic search over RDF triples
- Evidence building from graph neighborhoods
- LLM integration for query understanding
"""
import os
import sys
import pathlib
import json
from typing import List, Dict, Any, Optional, Tuple
from rdflib import Graph, URIRef, Literal
from SPARQLWrapper import SPARQLWrapper, JSON, TURTLE
import requests

# Import GraphDB client
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from ingest.graphdb_client import GraphDBClient


class SPARQLGraphRAG:
    """
    GraphRAG implementation using SPARQL queries over RDF graphs.
    """
    
    def __init__(
        self,
        graphdb_client: GraphDBClient,
        llm_client=None,
        max_hops: int = 3,
        top_k: int = 20
    ):
        """
        Initialize SPARQL GraphRAG.
        
        Args:
            graphdb_client: GraphDBClient instance
            llm_client: Optional LLM client for query generation
            max_hops: Maximum graph traversal hops
            top_k: Number of top results to retrieve
        """
        self.client = graphdb_client
        self.llm_client = llm_client
        self.max_hops = max_hops
        self.top_k = top_k
    
    def natural_language_to_sparql(
        self,
        question: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Convert natural language question to SPARQL query.
        
        This is a simplified version. In production, you'd use an LLM
        to generate SPARQL queries from natural language.
        
        Args:
            question: Natural language question
            context: Optional context for query generation
        
        Returns:
            SPARQL query string
        """
        question_lower = question.lower()
        
        # Simple keyword-based SPARQL generation
        # In production, use LLM (e.g., GPT-4, Claude) to generate proper SPARQL
        
        # Common patterns
        if "how many" in question_lower or "count" in question_lower:
            # Count query pattern
            if "door" in question_lower:
                return """
                PREFIX ifc: <http://ifc-ld.org/schemas/ifc2x3#>
                SELECT (COUNT(DISTINCT ?door) as ?count)
                WHERE {
                    ?door a ifc:IfcDoor .
                }
                """
            elif "window" in question_lower:
                return """
                PREFIX ifc: <http://ifc-ld.org/schemas/ifc2x3#>
                SELECT (COUNT(DISTINCT ?window) as ?count)
                WHERE {
                    ?window a ifc:IfcWindow .
                }
                """
            elif "space" in question_lower or "room" in question_lower:
                return """
                PREFIX ifc: <http://ifc-ld.org/schemas/ifc2x3#>
                SELECT (COUNT(DISTINCT ?space) as ?count)
                WHERE {
                    ?space a ifc:IfcSpace .
                }
                """
        
        # Search/find pattern
        if "find" in question_lower or "show" in question_lower or "list" in question_lower:
            if "door" in question_lower:
                return """
                PREFIX ifc: <http://ifc-ld.org/schemas/ifc2x3#>
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                SELECT ?door ?name ?type
                WHERE {
                    ?door a ifc:IfcDoor .
                    OPTIONAL { ?door ifc:name ?name }
                    OPTIONAL { ?door rdfs:label ?name }
                }
                LIMIT 50
                """
            elif "window" in question_lower:
                return """
                PREFIX ifc: <http://ifc-ld.org/schemas/ifc2x3#>
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                SELECT ?window ?name ?type
                WHERE {
                    ?window a ifc:IfcWindow .
                    OPTIONAL { ?window ifc:name ?name }
                    OPTIONAL { ?window rdfs:label ?name }
                }
                LIMIT 50
                """
        
        # Default: search for any IFC entity matching keywords
        keywords = [w for w in question.split() if len(w) > 3]
        if keywords:
            keyword_filter = " || ".join([f'CONTAINS(LCASE(?name), "{k.lower()}")' for k in keywords[:3]])
            return f"""
            PREFIX ifc: <http://ifc-ld.org/schemas/ifc2x3#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT ?entity ?name ?type
            WHERE {{
                ?entity a ?type .
                FILTER (STRSTARTS(STR(?type), "http://ifc-ld.org/schemas/ifc2x3#Ifc"))
                OPTIONAL {{ ?entity ifc:name ?name }}
                OPTIONAL {{ ?entity rdfs:label ?name }}
                FILTER ({keyword_filter})
            }}
            LIMIT 50
            """
        
        # Fallback: get all IFC entities
        return """
        PREFIX ifc: <http://ifc-ld.org/schemas/ifc2x3#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?entity ?name ?type
        WHERE {
            ?entity a ?type .
            FILTER (STRSTARTS(STR(?type), "http://ifc-ld.org/schemas/ifc2x3#Ifc"))
            OPTIONAL { ?entity ifc:name ?name }
            OPTIONAL { ?entity rdfs:label ?name }
        }
        LIMIT 50
        """
    
    def execute_sparql_query(self, query: str) -> Dict[str, Any]:
        """Execute SPARQL query and return results."""
        return self.client.execute_sparql_query(query, output_format="json")
    
    def expand_neighborhood(
        self,
        seed_uris: List[str],
        max_hops: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Expand graph neighborhood around seed URIs.
        
        Args:
            seed_uris: List of seed entity URIs
            max_hops: Maximum traversal hops (defaults to self.max_hops)
        
        Returns:
            Dictionary with nodes and edges
        """
        if max_hops is None:
            max_hops = self.max_hops
        
        # Build SPARQL query to get neighborhood
        seed_filter = " || ".join([f"?seed = <{uri}>" for uri in seed_uris[:10]])
        
        query = f"""
        PREFIX ifc: <http://ifc-ld.org/schemas/ifc2x3#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT DISTINCT ?seed ?entity ?predicate ?object ?name ?type
        WHERE {{
            VALUES ?seed {{ {seed_uris[0] if seed_uris else '?x'} }}
            
            {{
                # Direct connections from seed
                ?seed ?predicate ?object .
                BIND(?seed AS ?entity)
            }}
            UNION
            {{
                # Connections to seed
                ?entity ?predicate ?seed .
            }}
            UNION
            {{
                # Two-hop connections
                ?seed ?p1 ?intermediate .
                ?intermediate ?predicate ?object .
                BIND(?intermediate AS ?entity)
            }}
            
            OPTIONAL {{ ?entity ifc:name ?name }}
            OPTIONAL {{ ?entity rdfs:label ?name }}
            OPTIONAL {{ ?entity a ?type }}
        }}
        LIMIT 500
        """
        
        try:
            results = self.execute_sparql_query(query)
            
            # Parse results
            nodes = {}
            edges = []
            
            if "results" in results and "bindings" in results["results"]:
                for binding in results["results"]["bindings"]:
                    # Extract entity/node
                    entity_uri = binding.get("entity", {}).get("value") or \
                                binding.get("seed", {}).get("value")
                    object_uri = binding.get("object", {}).get("value")
                    predicate_uri = binding.get("predicate", {}).get("value")
                    
                    if entity_uri:
                        if entity_uri not in nodes:
                            nodes[entity_uri] = {
                                "id": entity_uri,
                                "name": binding.get("name", {}).get("value", ""),
                                "type": binding.get("type", {}).get("value", ""),
                            }
                    
                    # Extract edge
                    if entity_uri and object_uri and predicate_uri:
                        # Check if object is a URI (not a literal)
                        if object_uri.startswith("http"):
                            edges.append({
                                "src": entity_uri,
                                "dst": object_uri,
                                "type": predicate_uri.split("#")[-1] if "#" in predicate_uri else predicate_uri.split("/")[-1],
                            })
            
            return {
                "nodes": list(nodes.values()),
                "edges": edges,
            }
            
        except Exception as e:
            print(f"⚠️  Error expanding neighborhood: {e}")
            return {"nodes": [], "edges": []}
    
    def build_evidence(
        self,
        question: str,
        top_k: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Build evidence graph from natural language question.
        
        Args:
            question: Natural language question
            top_k: Number of top results (defaults to self.top_k)
        
        Returns:
            Evidence dictionary with question, focus seeds, nodes, and edges
        """
        if top_k is None:
            top_k = self.top_k
        
        # Generate SPARQL query from question
        sparql_query = self.natural_language_to_sparql(question)
        
        # Execute query to get seed entities
        results = self.execute_sparql_query(sparql_query)
        
        # Extract seed URIs
        seed_uris = []
        if "results" in results and "bindings" in results["results"]:
            for binding in results["results"]["bindings"]:
                # Try different possible keys for entity URI
                for key in ["entity", "door", "window", "space", "?entity"]:
                    if key in binding:
                        uri = binding[key].get("value")
                        if uri and uri.startswith("http"):
                            seed_uris.append(uri)
                            break
        
        # Expand neighborhood around seeds
        neighborhood = self.expand_neighborhood(seed_uris[:top_k])
        
        return {
            "question": question,
            "sparql_query": sparql_query,
            "focus_seeds": [{"id": uri, "score": 1.0} for uri in seed_uris[:top_k]],
            "nodes": neighborhood.get("nodes", []),
            "edges": neighborhood.get("edges", []),
        }


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="SPARQL-based GraphRAG for RDF graphs"
    )
    parser.add_argument("question", help="Natural language question")
    parser.add_argument("--base-url", default="http://localhost:7200",
                       help="GraphDB base URL")
    parser.add_argument("--repository", default="rig-facility-mgmt",
                       help="Repository name")
    parser.add_argument("--top-k", type=int, default=20,
                       help="Number of top results")
    parser.add_argument("--max-hops", type=int, default=3,
                       help="Maximum graph traversal hops")
    parser.add_argument("--output", default=None,
                       help="Output JSON file for evidence")
    
    args = parser.parse_args()
    
    # Initialize GraphDB client
    client = GraphDBClient(
        base_url=args.base_url,
        repository=args.repository
    )
    
    # Initialize GraphRAG
    rag = SPARQLGraphRAG(
        graphdb_client=client,
        max_hops=args.max_hops,
        top_k=args.top_k
    )
    
    # Build evidence
    evidence = rag.build_evidence(args.question, top_k=args.top_k)
    
    # Output results
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(evidence, f, indent=2)
        print(f"✅ Evidence saved to: {args.output}")
    else:
        print(json.dumps(evidence, indent=2))
    
    print(f"\n📊 Evidence Summary:")
    print(f"   Question: {evidence['question']}")
    print(f"   Focus seeds: {len(evidence['focus_seeds'])}")
    print(f"   Nodes: {len(evidence['nodes'])}")
    print(f"   Edges: {len(evidence['edges'])}")


if __name__ == "__main__":
    main()

