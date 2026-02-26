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
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from ingest.graphdb_client import GraphDBClient
from rag.sparql_rag import SPARQLGraphRAG

router = APIRouter()
logger = logging.getLogger("chat")

GRAPHDB_URL = os.getenv("GRAPHDB_URL", "http://localhost:7200")
GRAPHDB_REPOSITORY = os.getenv("GRAPHDB_REPOSITORY", "rig-facility-mgmt")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
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
    rag = _get_rag()
    oai = _get_openai()

    try:
        evidence = rag.build_evidence(request.message, top_k=15)
    except Exception as exc:
        logger.error("GraphRAG evidence build failed: %s", exc)
        evidence = {"question": request.message, "sparql_query": "", "focus_seeds": [], "nodes": [], "edges": []}

    context_block = _evidence_to_context(evidence)
    tool_action = _detect_tool_action(request.message, evidence)

    if not oai:
        reply = (
            f"[GraphRAG evidence collected — {len(evidence.get('nodes', []))} nodes, "
            f"{len(evidence.get('edges', []))} edges]\n\n{context_block}\n\n"
            "[Set OPENAI_API_KEY for natural language answers.]"
        )
        return {"reply": reply, "tool": tool_action, "evidence": _slim_evidence(evidence)}

    history = [{"role": "system", "content": SYSTEM_PROMPT}]
    for turn in request.history[-8:]:
        history.append({"role": turn.role if turn.role != "model" else "assistant", "content": turn.content})

    history.append({
        "role": "user",
        "content": (
            f"{request.message}\n\n"
            f"--- Graph Evidence ---\n{context_block}"
        ),
    })

    try:
        completion = oai.chat.completions.create(
            model=CHAT_MODEL,
            messages=history,
            temperature=0.3,
            max_tokens=800,
        )
        reply = completion.choices[0].message.content
    except Exception as exc:
        logger.error("OpenAI chat completion failed: %s", exc)
        reply = f"Graph evidence collected ({len(evidence.get('nodes', []))} nodes) but LLM call failed: {exc}"

    return {
        "reply": reply,
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
