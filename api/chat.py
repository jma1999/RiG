"""
GraphRAG Chat endpoint — the brain of Gemino.

Flow:
1. User sends a natural-language message.
2. SPARQLGraphRAG converts it to SPARQL (via OpenAI LLM), executes against GraphDB,
   extracts seed URIs, expands the neighborhood graph with decay-ranked scoring.
3. The evidence subgraph is serialised into a compact text context block.
4. The LLM generates a grounded, citation-rich answer using the evidence.
5. The response includes the SPARQL query used, the graph evidence, and tool actions
   so the frontend can update the Knowledge Graph Explorer and telemetry panels.
"""
import os
import sys
import pathlib
import json
import logging
import time
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
load_dotenv(pathlib.Path(__file__).resolve().parent.parent / ".env", override=True)

from fastapi import APIRouter
from pydantic import BaseModel

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from ingest.graphdb_client import GraphDBClient
# from rag.sparql_rag import SPARQLGraphRAG

from api.case_graphrag_adapter import run_case_graphrag

router = APIRouter()
logger = logging.getLogger("chat")

GRAPHDB_URL = os.getenv("GRAPHDB_URL", "http://localhost:7200")
GRAPHDB_REPOSITORY = os.getenv("GRAPHDB_REPOSITORY", "rig-ifcld")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip().strip('"').strip("'")
logger.info("OPENAI_API_KEY loaded: %s", "yes" if OPENAI_API_KEY else "NO")
CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", os.getenv("OPENAI_NL2SPARQL_MODEL", "gpt-4o-mini"))

SYSTEM_PROMPT = """\
You are Gemino, an AI facility management agent for the CASE Office building.
You have access to a semantic knowledge graph with four layers:
  - IFC-LD (building geometry: walls, doors, spaces, terminals)
  - Brick (room/floor/zone hierarchy, points)
  - ASHRAE 223P (sensors, observable properties, equipment)
  - Overlay (cross-ontology links via skos:exactMatch)

You also have access to live Disruptive Technologies sensor readings (humidity, \
presence, temperature) stored in TimescaleDB.

When answering:
- Always ground answers in the graph evidence provided.
- Cite specific entity labels or URIs when referencing building elements.
- If the evidence contains sensors, mention their mark labels (e.g. Sensor01).
- Be concise, technical, and helpful. Use bullet points for lists.
- If a question can't be answered from the evidence, say so honestly.
- When the user asks about telemetry/readings, mention the sensor mark and \
  its type (humidity, presence, temperature).
"""


class ChatTurn(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: List[ChatTurn] = []
    asset_context: Optional[str] = None


_rag: Optional[SPARQLGraphRAG] = None
_openai_client = None


def _get_rag() -> SPARQLGraphRAG:
    global _rag
    if _rag is None:
        client = GraphDBClient(
            base_url=GRAPHDB_URL,
            repository=GRAPHDB_REPOSITORY,
        )
        _rag = SPARQLGraphRAG(
            graphdb_client=client,
            max_hops=2,
            top_k=15,
            use_llm=True,
        )
    return _rag


def _get_openai():
    global _openai_client
    if _openai_client is None and OPENAI_API_KEY:
        try:
            from openai import OpenAI
            _openai_client = OpenAI(api_key=OPENAI_API_KEY)
        except ImportError:
            pass
    return _openai_client


def _evidence_to_context(evidence: Dict[str, Any], max_nodes: int = 30) -> str:
    """Serialize the graph evidence into a compact text block for the LLM."""
    lines = []
    sparql = evidence.get("sparql_query", "")
    if sparql:
        lines.append(f"SPARQL query used:\n{sparql}\n")

    seeds = evidence.get("focus_seeds", [])
    if seeds:
        seed_ids = [s["id"].split("/")[-1].split("#")[-1] for s in seeds[:10]]
        lines.append(f"Focus entities: {', '.join(seed_ids)}")

    nodes = evidence.get("nodes", [])[:max_nodes]
    if nodes:
        lines.append(f"\nGraph neighborhood ({len(nodes)} nodes):")
        for n in nodes:
            name = n.get("name") or n.get("id", "").split("/")[-1].split("#")[-1]
            ntype = (n.get("type") or "").split("#")[-1].split("/")[-1]
            hop = n.get("hop", "?")
            lines.append(f"  [{ntype}] {name} (hop={hop})")

    edges = evidence.get("edges", [])
    if edges:
        lines.append(f"\nRelationships ({len(edges)} edges):")
        for e in edges[:40]:
            src = e["src"].split("/")[-1].split("#")[-1]
            dst = e["dst"].split("/")[-1].split("#")[-1]
            rel = e.get("type", "related")
            lines.append(f"  {src} --{rel}--> {dst}")

    return "\n".join(lines)


def _detect_tool_action(message: str, evidence: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Detect if the chat should trigger a frontend tool action."""
    ml = message.lower()
    nodes = evidence.get("nodes", [])

    if any(w in ml for w in ("show graph", "visualize", "knowledge graph", "show me", "graph of")):
        graph_nodes = []
        graph_links = []
        node_ids = set()
        for n in nodes[:50]:
            nid = n.get("id", "")
            name = n.get("name") or nid.split("/")[-1].split("#")[-1]
            ntype = (n.get("type") or "").split("#")[-1]
            graph_nodes.append({"id": nid, "label": name, "name": name, "type": ntype, "status": "nominal"})
            node_ids.add(nid)
        for e in evidence.get("edges", []):
            if e["src"] in node_ids and e["dst"] in node_ids:
                graph_links.append({"source": e["src"], "target": e["dst"], "relationship": e.get("type", "related")})
        return {"action": "graph", "graphData": {"nodes": graph_nodes, "links": graph_links}}

    if any(w in ml for w in ("telemetry", "readings", "sensor data", "time series", "live data")):
        for n in nodes:
            name = (n.get("name") or "").lower()
            ntype = (n.get("type") or "").lower()
            if "sensor" in name or "sensor" in ntype:
                return {"action": "telemetry", "asset_id": n.get("id", ""), "query": message}
        return {"action": "telemetry", "query": message}

    if any(w in ml for w in ("search", "find", "where", "which", "list")):
        return {"action": "search", "query": message}

    return None


@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    t0 = time.time()

    try:
        result = run_case_graphrag(request.message)

        thinking_steps = result.get("thinking", [])
        elapsed_ms = int((time.time() - t0) * 1000)
        thinking_steps.append({
            "step": "done",
            "title": "Complete",
            "content": f"Answered in {elapsed_ms}ms",
        })

        return {
            "reply": result.get("reply", ""),
            "thinking": thinking_steps,
            "sparql_query": result.get("sparql_query", ""),
            "sql_query": result.get("sql_query", ""),
            "tool": result.get("tool"),
            "evidence": result.get("evidence", {}),
            "debug": result.get("debug", {}),
        }

    except Exception as exc:
        logger.exception("case_graphrag pipeline failed, falling back to legacy GraphRAG: %s", exc)

    # ------- legacy fallback path below -------
    thinking_steps = []
    thinking_steps.append({
        "step": "understanding",
        "title": "Understanding your question",
        "content": f"Analyzing: \"{request.message}\"",
    })

    rag = _get_rag()
    oai = _get_openai()

    sparql_query = ""
    evidence = {"question": request.message, "sparql_query": "", "focus_seeds": [], "nodes": [], "edges": []}

    try:
        sparql_query = rag.natural_language_to_sparql(request.message)
        thinking_steps.append({
            "step": "sparql",
            "title": "Generated SPARQL query",
            "content": sparql_query,
        })

        results = rag.execute_sparql_query(sparql_query)
        bindings = results.get("results", {}).get("bindings", [])
        thinking_steps.append({
            "step": "query_results",
            "title": "Query executed",
            "content": f"GraphDB returned {len(bindings)} bindings",
        })

        seed_uris = rag._extract_seed_uris_from_results(results, top_k=15)
        if not seed_uris:
            seed_uris = rag._recover_seeds_if_count_query(request.message, top_k=15)

        if seed_uris:
            neighborhood = rag.expand_neighborhood_with_ranking(
                seed_uris[:15],
                max_hops=2,
                top_k_nodes=45,
                question_keywords=[w for w in request.message.split() if len(w) > 3],
            )
            evidence = {
                "question": request.message,
                "sparql_query": sparql_query,
                "focus_seeds": [{"id": u, "score": 1.0} for u in seed_uris[:15]],
                "nodes": neighborhood["nodes"],
                "edges": neighborhood["edges"],
            }
            thinking_steps.append({
                "step": "evidence",
                "title": "Graph evidence collected",
                "content": f"Found {len(evidence['nodes'])} nodes and {len(evidence['edges'])} edges in neighborhood",
            })
        else:
            thinking_steps.append({
                "step": "evidence",
                "title": "No graph entities found",
                "content": "The query returned aggregate results or no matching entities",
            })

    except Exception as exc:
        logger.error("GraphRAG evidence build failed: %s", exc)
        thinking_steps.append({
            "step": "error",
            "title": "Graph query issue",
            "content": f"Could not query graph: {str(exc)[:200]}",
        })

    context_block = _evidence_to_context(evidence)
    tool_action = _detect_tool_action(request.message, evidence)

    if not oai:
        thinking_steps.append({
            "step": "llm",
            "title": "LLM not available",
            "content": "OPENAI_API_KEY is not configured. Returning raw evidence.",
        })
        reply = f"I found {len(evidence.get('nodes', []))} related entities in the knowledge graph.\n\n"
        if evidence.get("nodes"):
            for n in evidence["nodes"][:8]:
                name = n.get("name") or n.get("id", "").split("/")[-1].split("#")[-1]
                ntype = (n.get("type") or "").split("#")[-1]
                reply += f"• **{name}** ({ntype})\n"
        if not evidence.get("nodes"):
            reply += "No matching entities found. Try rephrasing your question."
        reply += "\n\n*Set OPENAI_API_KEY for full natural language answers.*"
    else:
        thinking_steps.append({
            "step": "generating",
            "title": "Generating answer",
            "content": f"Using {CHAT_MODEL} with graph evidence context",
        })

        history = [{"role": "system", "content": SYSTEM_PROMPT}]
        for turn in request.history[-8:]:
            history.append({"role": turn.role if turn.role != "model" else "assistant", "content": turn.content})

        history.append({
            "role": "user",
            "content": f"{request.message}\n\n--- Graph Evidence ---\n{context_block}",
        })

        try:
            completion = oai.chat.completions.create(
                model=CHAT_MODEL,
                messages=history,
                max_completion_tokens=800,
            )
            reply = completion.choices[0].message.content
        except Exception as exc:
            logger.error("OpenAI chat completion failed: %s", exc)
            reply = (
                f"I queried the knowledge graph and found {len(evidence.get('nodes', []))} entities, "
                f"but the language model could not generate a response: {str(exc)[:150]}\n\n"
                "The SPARQL query used is shown in the thinking section above."
            )

    elapsed_ms = int((time.time() - t0) * 1000)
    thinking_steps.append({
        "step": "done",
        "title": "Complete",
        "content": f"Answered in {elapsed_ms}ms",
    })

    return {
        "reply": reply,
        "thinking": thinking_steps,
        "sparql_query": sparql_query,
        "tool": tool_action,
        "evidence": _slim_evidence(evidence),
    }


def _slim_evidence(evidence: Dict[str, Any]) -> Dict[str, Any]:
    """Return a lightweight evidence summary for the frontend."""
    return {
        "sparql_query": evidence.get("sparql_query", ""),
        "seed_count": len(evidence.get("focus_seeds", [])),
        "node_count": len(evidence.get("nodes", [])),
        "edge_count": len(evidence.get("edges", [])),
        "seeds": [s["id"] for s in evidence.get("focus_seeds", [])[:5]],
    }


from api.main import app  # noqa: E402
app.include_router(router)
