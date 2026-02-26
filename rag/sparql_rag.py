# rag/sparql_rag.py
"""
SPARQL-based GraphRAG for RDF Graphs.

Fixes vs prior version:
- Correct seed extraction from SPARQL JSON results (keys are variable names, not '?x').
- Handles COUNT-only queries (no URIs) by running a follow-up seed query to fetch example instances.
- Uses IFC-LD lowercase localnames (ifc:ifcdoor, ifc:ifcwallstandardcase, etc.)
- Light auto-detection of IFC2x3 vs IFC4 (falls back to ifc2x3).
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


SCHEMA_CONTEXT = """
The RDF graph has 4 named graphs:

1. IFC-LD graph (<https://example.com/case-office/g/ifcld>):
   PREFIX ifc: <http://ifc-ld.org/schemas/ifc2x3#>
   Types are lowercase: ifc:ifcdoor, ifc:ifcwindow, ifc:ifcwall, ifc:ifcspace,
   ifc:ifcbuildingstorey, ifc:ifcflowterminal, ifc:ifcflowsegment, ifc:ifcsensor, etc.

2. Brick graph (<https://example.com/case-office/g/brick>):
   PREFIX brick1: <http://brickschema.org/schema/1.1.0/Brick#>
   Types: brick1:Floor, brick1:Room, brick1:HVAC_ZONE
   Properties: brick1:hasPart, brick1:isPartOf

3. ASHRAE 223P graph (<https://example.com/case-office/g/223p>):
   PREFIX s223: <http://data.ashrae.org/standard223#>
   Types: s223:PhysicalSpace, s223:Zone, s223:HumiditySensor, s223:OccupantPresenceSensor,
   s223:QuantifiableObservableProperty, s223:Equipment
   Properties: s223:hasPhysicalLocation, s223:observes, s223:hasZone, s223:hasProperty

4. Overlay graph (<https://example.com/case-office/g/overlay>):
   PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
   PREFIX brick1: <http://brickschema.org/schema/1.1.0/Brick#>
   Links entities across ontologies via skos:exactMatch and brick1:isPointOf.
   Brick rooms <-> IFC spaces, Brick points <-> IFC sensors.

Other prefixes:
- rdfs: <http://www.w3.org/2000/01/rdf-schema#>
- rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
- qudt: <http://qudt.org/schema/qudt/>
- quantitykind: <http://qudt.org/vocab/quantitykind/>

Use GRAPH clauses when targeting a specific layer.
For cross-layer queries, query the overlay graph for skos:exactMatch links.
Sensor marks (e.g. "Sensor01") are rdfs:label values on s223 sensor entities in the 223p graph.

Generate valid SPARQL 1.1. Return ONLY the SPARQL query, no explanation.
Use SELECT queries. For counts use (COUNT(DISTINCT ?x) as ?count). LIMIT 50 for lists.
"""


ENTITY_TO_CLASSES = {
    "door": ["ifcdoor", "ifcdoorstandardcase"],
    "window": ["ifcwindow", "ifcwindowstandardcase"],
    "wall": ["ifcwall", "ifcwallstandardcase"],
    "space": ["ifcspace"],
    "room": ["ifcspace"],
    "storey": ["ifcbuildingstorey"],
    "floor": ["ifcbuildingstorey", "ifcslab"],
    "slab": ["ifcslab"],
    "column": ["ifccolumn"],
    "beam": ["ifcbeam"],
    "roof": ["ifcroof"],
    "stair": ["ifcstair"],
    "terminal": ["ifcflowterminal"],
    "duct": ["ifcflowsegment"],
    "pipe": ["ifcflowsegment"],
    "sensor": ["ifcsensor"],
    "actuator": ["ifcactuator"],
}

ENTITY_TO_223P = {
    "sensor": "s223:Sensor",
    "humidity": "s223:HumiditySensor",
    "presence": "s223:OccupantPresenceSensor",
    "temperature": "s223:TemperatureSensor",
    "equipment": "s223:Equipment",
    "zone": "s223:Zone",
    "space": "s223:PhysicalSpace",
}

ENTITY_TO_BRICK = {
    "room": "brick1:Room",
    "floor": "brick1:Floor",
    "zone": "brick1:HVAC_ZONE",
}


def _get_openai_client():
    api_key = (os.getenv("OPENAI_API_KEY") or "").strip().strip('"').strip("'")
    if not api_key:
        return None
    try:
        from openai import OpenAI
        return OpenAI(api_key=api_key)
    except ImportError:
        return None


def _llm_natural_language_to_sparql(question: str, schema_context: str = SCHEMA_CONTEXT) -> Optional[str]:
    client = _get_openai_client()
    if not client:
        return None

    model = os.getenv("OPENAI_NL2SPARQL_MODEL", "gpt-4o-mini")

    system_msg = (
        "You generate SPARQL 1.1 queries for a multi-ontology building knowledge graph "
        "stored in GraphDB with named graphs. "
        "Output only valid SPARQL, no markdown fences or explanation. "
        "When querying across ontologies, use GRAPH clauses and the overlay graph "
        "for skos:exactMatch cross-references."
    )

    prompt = f"""{schema_context}

Question: {question}

SPARQL query:"""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=1024,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        return raw.strip()
    except Exception as e:
        print(f"LLM SPARQL generation failed: {e}")
        return None


def _guess_entity_from_question(question: str) -> Optional[str]:
    ql = question.lower()
    for k in ENTITY_TO_CLASSES.keys():
        if k in ql:
            return k
    return None


def _heuristic_natural_language_to_sparql(question: str, ifc_prefix: str) -> str:
    """Keyword-based fallback when LLM is unavailable."""
    ql = question.lower()

    # Count patterns
    if "how many" in ql or "count" in ql:
        ent = _guess_entity_from_question(question)
        if ent:
            classes = ENTITY_TO_CLASSES[ent]
            union = "\n  UNION\n".join([f"  {{ ?x a ifc:{c} . }}" for c in classes])
            return f"""
PREFIX ifc: <{ifc_prefix}>
SELECT (COUNT(DISTINCT ?x) as ?count)
WHERE {{
{union}
}}
""".strip()

    # List patterns
    if any(w in ql for w in ("find", "show", "list")):
        ent = _guess_entity_from_question(question)
        if ent:
            classes = ENTITY_TO_CLASSES[ent]
            union = "\n  UNION\n".join([f"  {{ ?x a ifc:{c} . }}" for c in classes])
            return f"""
PREFIX ifc: <{ifc_prefix}>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?x ?name ?type
WHERE {{
{union}
  OPTIONAL {{ ?x ifc:name ?name }}
  OPTIONAL {{ ?x rdfs:label ?name }}
  OPTIONAL {{ ?x a ?type }}
}}
LIMIT 50
""".strip()

    # Generic keyword search fallback
    keywords = [w for w in question.split() if len(w) > 3]
    if keywords:
        kf = " || ".join([f'CONTAINS(LCASE(STR(?name)), "{k.lower()}")' for k in keywords[:3]])
        return f"""
PREFIX ifc: <{ifc_prefix}>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?entity ?name ?type
WHERE {{
  ?entity a ?type .
  FILTER (STRSTARTS(STR(?type), "http://ifc-ld.org/schemas/"))
  OPTIONAL {{ ?entity ifc:name ?name }}
  OPTIONAL {{ ?entity rdfs:label ?name }}
  BIND(COALESCE(?name, "") AS ?name)
  FILTER ({kf})
}}
LIMIT 50
""".strip()

    return f"""
PREFIX ifc: <{ifc_prefix}>
SELECT ?entity ?type
WHERE {{
  ?entity a ?type .
  FILTER (STRSTARTS(STR(?type), "http://ifc-ld.org/schemas/"))
}}
LIMIT 50
""".strip()


class SPARQLGraphRAG:
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
        self.ifc_prefix = self._detect_ifc_prefix()

    def _detect_ifc_prefix(self) -> str:
        """
        Very lightweight detection: check if any types in repo start with ifc4#.
        Falls back to ifc2x3#.
        """
        try:
            q = """
SELECT ?t WHERE {
  ?s a ?t .
  FILTER(STRSTARTS(STR(?t), "http://ifc-ld.org/schemas/ifc4#"))
} LIMIT 1
""".strip()
            res = self.client.execute_sparql_query(q, output_format="json")
            bindings = res.get("results", {}).get("bindings", [])
            if bindings:
                return IFC4_PREFIX
        except Exception:
            pass
        return IFC2X3_PREFIX

    def natural_language_to_sparql(self, question: str) -> str:
        if self.use_llm:
            sparql = _llm_natural_language_to_sparql(question)
            if sparql:
                return sparql
        return _heuristic_natural_language_to_sparql(question, self.ifc_prefix)

    def execute_sparql_query(self, query: str) -> Dict[str, Any]:
        return self.client.execute_sparql_query(query, output_format="json")

    def _extract_seed_uris_from_results(self, results: Dict[str, Any], top_k: int) -> List[str]:
        """
        Extract URI values from SPARQL JSON bindings.
        Important: keys are variable names WITHOUT '?'.
        """
        seed_uris: List[str] = []
        bindings = results.get("results", {}).get("bindings", [])

        for b in bindings:
            # pick first URI-like term in the binding row
            for var, cell in b.items():
                v = cell.get("value")
                t = cell.get("type")
                if t in ("uri", "bnode") and v and v.startswith("http"):
                    seed_uris.append(v)
                    break

            if len(seed_uris) >= top_k:
                break

        return seed_uris

    def _recover_seeds_if_count_query(self, question: str, top_k: int) -> List[str]:
        """
        If query result is only literals (e.g., COUNT), fetch instance URIs as seeds
        so the neighborhood graph isn't empty.
        """
        ent = _guess_entity_from_question(question)
        if not ent:
            return []

        classes = ENTITY_TO_CLASSES[ent]
        union = "\n  UNION\n".join([f"  {{ ?x a ifc:{c} . }}" for c in classes])

        q = f"""
PREFIX ifc: <{self.ifc_prefix}>
SELECT DISTINCT ?x
WHERE {{
{union}
}}
LIMIT {top_k}
""".strip()

        try:
            res = self.execute_sparql_query(q)
            return self._extract_seed_uris_from_results(res, top_k)
        except Exception:
            return []

    def _expand_neighborhood_hop(
        self,
        seed_uris: List[str],
        hop: int,
        limit: int = 500,
    ) -> Tuple[List[Dict], List[Dict]]:
        if not seed_uris:
            return [], []

        values_clause = " ".join(f"<{u}>" for u in seed_uris[:20])

        query = f"""
PREFIX ifc: <{self.ifc_prefix}>
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

  FILTER (isIRI(?subj) && isIRI(?obj))
}}
LIMIT {limit}
""".strip()

        try:
            results = self.execute_sparql_query(query)
            nodes: Dict[str, Dict[str, Any]] = {}
            edges: List[Dict[str, Any]] = []

            for b in results.get("results", {}).get("bindings", []):
                s = b.get("subj", {}).get("value")
                p = b.get("pred", {}).get("value")
                o = b.get("obj", {}).get("value")
                if not (s and p and o):
                    continue

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
        max_hops = max_hops or self.max_hops
        top_k_nodes = top_k_nodes or (self.top_k * 2)
        keywords = (question_keywords or [])

        # ✅ Include seeds as first-class nodes so their edges don't get filtered out later
        all_nodes: Dict[str, Dict[str, Any]] = {
            u: {"id": u, "name": "", "type": "", "hop": 0} for u in seed_uris[:20]
        }
        all_edges: List[Dict[str, Any]] = []

        frontier = list(seed_uris[:20])
        seen = set(seed_uris[:20])

        for hop in range(1, max_hops + 1):
            if not frontier:
                break

            nodes_batch, edges_batch = self._expand_neighborhood_hop(frontier, hop)
            next_frontier: List[str] = []

            for n in nodes_batch:
                uid = n["id"]
                # keep best (closest) hop if we see it again
                if uid not in all_nodes or n.get("hop", hop) < all_nodes[uid].get("hop", hop):
                    all_nodes[uid] = n

                if uid not in seen:
                    seen.add(uid)
                    next_frontier.append(uid)

            all_edges.extend(edges_batch)
            frontier = next_frontier

        # degree for scoring
        degree = defaultdict(int)
        for e in all_edges:
            degree[e["src"]] += 1
            degree[e["dst"]] += 1

        # score nodes
        scored = []
        for uid, n in all_nodes.items():
            hop_val = n.get("hop", 1)
            hop_score = 2.0 if hop_val == 0 else 1.0 / hop_val  # ✅ seeds get strong score
            deg_score = min(degree[uid] / 10.0, 1.0) * 0.2

            kw_score = 0.0
            name_lower = (n.get("name") or "").lower()
            type_str = (n.get("type") or "").lower()
            for k in keywords:
                kk = k.lower()
                if kk in name_lower or kk in type_str:
                    kw_score = 0.3
                    break

            scored.append((hop_score + deg_score + kw_score, uid, n))

        scored.sort(key=lambda x: -x[0])
        top_nodes = [n for _, _, n in scored[:top_k_nodes]]

        # ✅ Always keep seed nodes in the edge subgraph
        top_ids = {n["id"] for n in top_nodes}.union(set(seed_uris[:20]))

        filtered_edges = [e for e in all_edges if e["src"] in top_ids and e["dst"] in top_ids]

        return {"nodes": top_nodes, "edges": filtered_edges}

    def build_evidence(self, question: str, top_k: Optional[int] = None) -> Dict[str, Any]:
        top_k = top_k or self.top_k
        keywords = [w for w in question.split() if len(w) > 3]

        sparql_query = self.natural_language_to_sparql(question)
        results = self.execute_sparql_query(sparql_query)

        seed_uris = self._extract_seed_uris_from_results(results, top_k=top_k)

        # If query returned only literals (e.g., COUNT), recover instance seeds
        if not seed_uris:
            seed_uris = self._recover_seeds_if_count_query(question, top_k=top_k)

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
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(evidence, f, indent=2)
        print(f"✅ Evidence saved to: {args.output}")
    else:
        print(json.dumps(evidence, indent=2))

    print(f"\n📊 Evidence Summary:")
    print(f"   Question: {evidence['question']}")
    print(f"   IFC prefix: {rag.ifc_prefix}")
    print(f"   Focus seeds: {len(evidence['focus_seeds'])}")
    print(f"   Nodes: {len(evidence['nodes'])}")
    print(f"   Edges: {len(evidence['edges'])}")


if __name__ == "__main__":
    main()
