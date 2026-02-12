# rag/sparql_rag.py
"""
SPARQL-based GraphRAG for RDF Graphs.

This module provides GraphRAG functionality using SPARQL queries over RDF graphs
stored in GraphDB.

Key features:
- LLM-based natural language to SPARQL conversion (OpenAI)
- Keyword heuristics fallback when LLM unavailable
- Neighborhood expansion with ranking for graph traversal
- Evidence building from ranked graph neighborhoods
"""
import os
import sys
import pathlib
import json
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from ingest.graphdb_client import GraphDBClient

# IFC-LD schema prefixes (support both IFC2x3 and IFC4)
IFC2X3_PREFIX = "http://ifc-ld.org/schemas/ifc2x3#"
IFC4_PREFIX = "http://ifc-ld.org/schemas/ifc4#"

# Schema context for LLM - core IFC-LD classes and properties
SCHEMA_CONTEXT = """
The RDF graph uses IFC-LD ontology. Key prefixes:
- ifc: <http://ifc-ld.org/schemas/ifc2x3#> (or ifc4# for IFC4 models)
- rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
- rdfs: <http://www.w3.org/2000/01/rdf-schema#>

Common IFC classes: IfcDoor, IfcWindow, IfcWall, IfcSpace, IfcBuildingStorey, IfcBuilding,
IfcFlowTerminal, IfcFlowSegment, IfcFlowController, IfcDistributionElement, IfcSystem,
IfcSlab, IfcColumn, IfcBeam, IfcStair, IfcRoof, IfcDuctTerminal, IfcDistributionPort.

Common properties: name (or name_IfcRoot), objectType, description.
Containment: containsElements, containedInStructure, relatingStructure, relatedElements.
Spatial: IfcRelContainedInSpatialStructure links elements to storeys/spaces.
Type: rdf:type for class; objectTypeOf for type objects.

Generate valid SPARQL 1.1. Return ONLY the SPARQL query, no explanation.
Use SELECT queries. For counts use (COUNT(DISTINCT ?x) as ?count). LIMIT 50 for lists.
"""


def _get_openai_client():
    """Lazy-load OpenAI client if API key is set."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI
        return OpenAI(api_key=api_key)
    except ImportError:
        return None


def _llm_natural_language_to_sparql(question: str, schema_context: str = SCHEMA_CONTEXT) -> Optional[str]:
    """
    Convert natural language to SPARQL using OpenAI LLM.
    Returns None if LLM is unavailable.
    """
    client = _get_openai_client()
    if not client:
        return None

    model = os.getenv("OPENAI_NL2SPARQL_MODEL", "gpt-4o-mini")

    prompt = f"""You are a SPARQL expert. Convert this natural language question about a building/facility IFC graph into a SPARQL query.

{schema_context}

Question: {question}

SPARQL query:"""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You generate SPARQL queries for IFC-LD RDF graphs. Output only valid SPARQL, no markdown or explanation."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=1024,
        )
        raw = response.choices[0].message.content.strip()
        # Strip markdown code blocks if present
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        return raw
    except Exception as e:
        print(f"⚠️  LLM SPARQL generation failed: {e}")
        return None


def _heuristic_natural_language_to_sparql(question: str) -> str:
    """Keyword-based fallback when LLM is unavailable."""
    ql = question.lower()

    # Count patterns
    if "how many" in ql or "count" in ql:
        for entity, cls in [("door", "IfcDoor"), ("window", "IfcWindow"), ("space", "IfcSpace"),
                           ("room", "IfcSpace"), ("wall", "IfcWall"), ("storey", "IfcBuildingStorey")]:
            if entity in ql:
                return f"""
                PREFIX ifc: <{IFC2X3_PREFIX}>
                SELECT (COUNT(DISTINCT ?x) as ?count)
                WHERE {{ ?x a ifc:{cls} . }}
                """

    # List/find patterns
    if "find" in ql or "show" in ql or "list" in ql:
        for entity, cls in [("door", "IfcDoor"), ("window", "IfcWindow"), ("space", "IfcSpace"),
                           ("wall", "IfcWall"), ("terminal", "IfcFlowTerminal"), ("duct", "IfcFlowSegment")]:
            if entity in ql:
                return f"""
                PREFIX ifc: <{IFC2X3_PREFIX}>
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                SELECT ?x ?name ?type
                WHERE {{
                    ?x a ifc:{cls} .
                    OPTIONAL {{ ?x ifc:name ?name }}
                    OPTIONAL {{ ?x rdfs:label ?name }}
                    BIND("{cls}" as ?type)
                }}
                LIMIT 50
                """

    # Keyword search
    keywords = [w for w in question.split() if len(w) > 3]
    if keywords:
        kf = " || ".join([f'CONTAINS(LCASE(COALESCE(?name,"")), "{k.lower()}")' for k in keywords[:3]])
        return f"""
        PREFIX ifc: <{IFC2X3_PREFIX}>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?entity ?name ?type
        WHERE {{
            ?entity a ?type .
            FILTER (STRSTARTS(STR(?type), "http://ifc-ld.org/schemas/"))
            OPTIONAL {{ ?entity ifc:name ?name }}
            OPTIONAL {{ ?entity rdfs:label ?name }}
            FILTER ({kf})
        }}
        LIMIT 50
        """

    # Fallback
    return f"""
    PREFIX ifc: <{IFC2X3_PREFIX}>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?entity ?name ?type
    WHERE {{
        ?entity a ?type .
        FILTER (STRSTARTS(STR(?type), "http://ifc-ld.org/schemas/"))
        OPTIONAL {{ ?entity ifc:name ?name }}
        OPTIONAL {{ ?entity rdfs:label ?name }}
    }}
    LIMIT 50
    """


class SPARQLGraphRAG:
    """
    GraphRAG implementation using SPARQL over RDF graphs.
    Supports LLM-based NL-to-SPARQL and neighborhood expansion ranking.
    """

    def __init__(
        self,
        graphdb_client: GraphDBClient,
        llm_client=None,
        max_hops: int = 3,
        top_k: int = 20,
        use_llm: bool = True,
    ):
        self.client = graphdb_client
        self.llm_client = llm_client
        self.max_hops = max_hops
        self.top_k = top_k
        self.use_llm = use_llm and bool(os.getenv("OPENAI_API_KEY"))

    def natural_language_to_sparql(
        self,
        question: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Convert natural language to SPARQL.
        Uses LLM if OPENAI_API_KEY is set, else keyword heuristics.
        """
        if self.use_llm:
            sparql = _llm_natural_language_to_sparql(question)
            if sparql:
                return sparql
        return _heuristic_natural_language_to_sparql(question)

    def execute_sparql_query(self, query: str) -> Dict[str, Any]:
        """Execute SPARQL query and return results."""
        return self.client.execute_sparql_query(query, output_format="json")

    def _expand_neighborhood_hop(
        self,
        seed_uris: List[str],
        hop: int,
        limit: int = 500,
    ) -> Tuple[List[Dict], List[Dict]]:
        """Get one hop of neighborhood from seed URIs. Returns (nodes, edges)."""
        if not seed_uris:
            return [], []

        values_clause = " ".join(f"<{u}>" for u in seed_uris[:20])
        # Query both directions: seed->? and ?->seed
        query = f"""
        PREFIX ifc: <{IFC2X3_PREFIX}>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT DISTINCT ?subj ?pred ?obj ?subjName ?objName ?subjType ?objType
        WHERE {{
            VALUES ?seed {{ {values_clause} }}
            {{
                ?seed ?pred ?obj .
                BIND(?seed AS ?subj)
            }}
            UNION
            {{
                ?subj ?pred ?seed .
                BIND(?seed AS ?obj)
            }}
            OPTIONAL {{ ?subj ifc:name ?subjName }}
            OPTIONAL {{ ?subj rdfs:label ?subjName }}
            OPTIONAL {{ ?subj a ?subjType }}
            OPTIONAL {{ ?obj ifc:name ?objName }}
            OPTIONAL {{ ?obj rdfs:label ?objName }}
            OPTIONAL {{ ?obj a ?objType }}
            FILTER (STRSTARTS(STR(?subj), "http") && STRSTARTS(STR(?obj), "http"))
        }}
        LIMIT {limit}
        """
        try:
            results = self.execute_sparql_query(query)
            nodes = {}
            edges = []
            if "results" in results and "bindings" in results["results"]:
                for b in results["results"]["bindings"]:
                    s = b.get("subj", {}).get("value")
                    p = b.get("pred", {}).get("value")
                    o = b.get("obj", {}).get("value")
                    if s and o and p and o.startswith("http"):
                        nodes[s] = {
                            "id": s,
                            "name": b.get("subjName", {}).get("value", ""),
                            "type": b.get("subjType", {}).get("value", ""),
                            "hop": hop,
                        }
                        nodes[o] = {
                            "id": o,
                            "name": b.get("objName", {}).get("value", ""),
                            "type": b.get("objType", {}).get("value", ""),
                            "hop": hop,
                        }
                        pred_short = p.split("#")[-1] if "#" in p else p.split("/")[-1]
                        edges.append({"src": s, "dst": o, "type": pred_short})
            return list(nodes.values()), edges
        except Exception as e:
            print(f"⚠️  Neighborhood expansion error: {e}")
            return [], []

    def expand_neighborhood_with_ranking(
        self,
        seed_uris: List[str],
        max_hops: Optional[int] = None,
        top_k_nodes: Optional[int] = None,
        question_keywords: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Expand graph neighborhood with ranking.

        Strategy:
        1. Expand iteratively 1 hop at a time
        2. Rank nodes by: hop distance (closer = higher), degree (more connections = higher)
        3. Optionally boost nodes whose name/type matches question keywords
        4. Return top-k nodes by combined score
        """
        max_hops = max_hops or self.max_hops
        top_k_nodes = top_k_nodes or (self.top_k * 2)
        keywords = (question_keywords or []) if question_keywords else []

        all_nodes = {}
        all_edges = []
        frontier = list(seed_uris[:20])
        seen = set(seed_uris)

        for hop in range(1, max_hops + 1):
            if not frontier:
                break
            nodes_batch, edges_batch = self._expand_neighborhood_hop(frontier, hop)
            next_frontier = []

            for n in nodes_batch:
                uid = n["id"]
                if uid not in seen:
                    seen.add(uid)
                    all_nodes[uid] = n
                    next_frontier.append(uid)

            for e in edges_batch:
                if (e["src"], e["dst"]) not in {(x["src"], x["dst"]) for x in all_edges}:
                    all_edges.append(e)

            frontier = next_frontier

        # Ranking: score = 1/hop + 0.1 * degree + keyword_match_boost
        degree = defaultdict(int)
        for e in all_edges:
            degree[e["src"]] += 1
            degree[e["dst"]] += 1

        scored = []
        for uid, n in all_nodes.items():
            hop_val = n.get("hop", 1)
            hop_score = 1.0 / hop_val if hop_val > 0 else 1.0
            deg_score = min(degree[uid] / 10.0, 1.0) * 0.2
            kw_score = 0.0
            name_lower = (n.get("name") or "").lower()
            type_str = (n.get("type") or "").lower()
            for k in keywords:
                if k.lower() in name_lower or k.lower() in type_str:
                    kw_score += 0.3
                    break
            score = hop_score + deg_score + kw_score
            scored.append((score, uid, n))

        scored.sort(key=lambda x: -x[0])
        top = [n for _, _, n in scored[:top_k_nodes]]

        # Filter edges to only include top nodes
        top_ids = {n["id"] for n in top}
        filtered_edges = [e for e in all_edges if e["src"] in top_ids and e["dst"] in top_ids]

        return {"nodes": top, "edges": filtered_edges}

    def expand_neighborhood(
        self,
        seed_uris: List[str],
        max_hops: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Expand graph neighborhood (legacy interface).
        Delegates to expand_neighborhood_with_ranking.
        """
        result = self.expand_neighborhood_with_ranking(
            seed_uris, max_hops=max_hops, question_keywords=None
        )
        return {"nodes": result["nodes"], "edges": result["edges"]}

    def build_evidence(
        self,
        question: str,
        top_k: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Build evidence graph from natural language question.
        Uses LLM-based SPARQL generation and neighborhood expansion ranking.
        """
        top_k = top_k or self.top_k
        keywords = [w for w in question.split() if len(w) > 3]

        sparql_query = self.natural_language_to_sparql(question)
        results = self.execute_sparql_query(sparql_query)

        seed_uris = []
        if "results" in results and "bindings" in results["results"]:
            for binding in results["results"]["bindings"]:
                for key in list(binding.keys()):
                    if key.startswith("?") or key in ("entity", "door", "window", "space", "x"):
                        val = binding[key].get("value")
                        if val and val.startswith("http"):
                            seed_uris.append(val)
                            break

        neighborhood = self.expand_neighborhood_with_ranking(
            seed_uris[:top_k],
            max_hops=self.max_hops,
            top_k_nodes=top_k * 3,
            question_keywords=keywords,
        )

        return {
            "question": question,
            "sparql_query": sparql_query,
            "focus_seeds": [{"id": u, "score": 1.0} for u in seed_uris[:top_k]],
            "nodes": neighborhood["nodes"],
            "edges": neighborhood["edges"],
        }


def main():
    import argparse

    parser = argparse.ArgumentParser(description="SPARQL-based GraphRAG for RDF graphs")
    parser.add_argument("question", help="Natural language question")
    parser.add_argument("--base-url", default="http://localhost:7200", help="GraphDB base URL")
    parser.add_argument("--repository", default="rig-facility-mgmt", help="Repository name")
    parser.add_argument("--top-k", type=int, default=20, help="Number of top results")
    parser.add_argument("--max-hops", type=int, default=3, help="Maximum graph traversal hops")
    parser.add_argument("--output", default=None, help="Output JSON file for evidence")
    parser.add_argument("--no-llm", action="store_true", help="Disable LLM, use heuristics only")

    args = parser.parse_args()

    client = GraphDBClient(base_url=args.base_url, repository=args.repository)

    rag = SPARQLGraphRAG(
        graphdb_client=client,
        max_hops=args.max_hops,
        top_k=args.top_k,
        use_llm=not args.no_llm,
    )

    evidence = rag.build_evidence(args.question, top_k=args.top_k)

    if args.output:
        with open(args.output, "w") as f:
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
