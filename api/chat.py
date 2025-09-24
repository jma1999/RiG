import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from groq import Groq
from pydantic import BaseModel

from api.main import (
    app,
    pick_count_types,
    count as count_endpoint,
    semantic_search,
)


router = APIRouter()

client = Groq(api_key=os.environ["GROQ_API_KEY"])

LLAMA_MODEL = "llama3-70b-8192"
SYSTEM_PROMPT = (
    "You are RiG’s facility assistant. "
    "You can access graph tools (count/search/asset) and must translate their "
    "results into friendly facility language. "
    "Always cite factual findings and suggest follow-up steps if helpful."
)


class ChatTurn(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    history: List[ChatTurn] = []
    asset_context: Optional[str] = None  # optional current asset id


def run_graph_tools(message: str) -> Dict[str, Any]:
    types = pick_count_types(message)
    if types:
        try:
            result = count_endpoint(q=message)
            return {"action": "count", "data": result}
        except Exception:
            pass

    hits, subgraphs = semantic_search(message)
    return {
        "action": "search",
        "hits": [h.model_dump() for h in hits],
        "subgraphs": [s.model_dump() for s in subgraphs],
    }


def render_tool_summary(payload: Dict[str, Any]) -> str:
    action = payload.get("action")
    if action == "count":
        data = payload.get("data", {})
        parts = data.get("types", [])
        if not parts:
            return "Count tool did not return any results."
        lines = [f"{p['type']}: {p['count']}" for p in parts]
        return "Count results:\n" + "\n".join(lines)

    if action == "search":
        hits = payload.get("hits", [])[:5]
        if not hits:
            return "No matching graph entities were found."
        lines = []
        for h in hits:
            label = h.get("name") or h.get("id")
            lines.append(f"- {label} ({h.get('type','unknown')}) score={h.get('score',0):.2f}")
        return "Top graph hits:\n" + "\n".join(lines)

    return "No tool context available."


@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    tool_payload = run_graph_tools(request.message)
    tool_summary = render_tool_summary(tool_payload)

    history: List[Dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    for turn in request.history[-6:]:
        history.append({"role": turn.role, "content": turn.content})

    history.append(
        {
            "role": "user",
            "content": f"{request.message}\n\nContext:\n{tool_summary}",
        }
    )

    completion = client.chat.completions.create(
        model=LLAMA_MODEL,
        messages=history,
        temperature=0.4,
        max_tokens=600,
    )
    reply = completion.choices[0].message.content

    return {"reply": reply, "tool": tool_payload}


app.include_router(router)
