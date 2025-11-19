from __future__ import annotations
import os, json, threading, uuid
from typing import List, Dict, Any, Optional
from math import sqrt
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request, UploadFile, File, Form, Body, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import numpy as np
import re
from datetime import datetime

load_dotenv()
NEO4J_URI  = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASSWORD", "changeme123")
NEO4J_DB   = os.getenv("NEO4J_DATABASE", "neo4j")

INDEX_PATH = os.getenv("RAG_INDEX_PATH", "data/processed/rag/index.faiss")
META_PATH  = os.getenv("RAG_META_PATH",  "data/processed/rag/meta.json")
# Unify embedding model env var across repo
MODEL_NAME = os.getenv("EMBEDDING_MODEL", os.getenv("RAG_MODEL", "sentence-transformers/all-MiniLM-L6-v2"))
os.environ.setdefault("TRANSFORMERS_NO_TORCH_FLEX_ATTENTION", "1")

app = FastAPI(title="RiG GraphRAG API", version="0.1")
app.mount("/app", StaticFiles(directory="web", html=True), name="app")

# CORS: prefer env-only; always allow localhost for dev
cors_origins = []
extra_origins = os.getenv("FRONTEND_ORIGINS")
if extra_origins:
    cors_origins.extend([o.strip() for o in extra_origins.split(",") if o.strip()])
cors_origins.extend(["http://localhost:5173", "http://127.0.0.1:5173"])  # dev convenience
if os.getenv("DEV_ALLOW_ALL_ORIGINS") == "1":
    cors_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    # Always send JSON so the web UI doesn't choke on HTML error pages
    return JSONResponse(status_code=500, content={"error": str(exc)})


# Helpful root endpoint so external GET / won't return 404 spam
@app.get("/")
def root():
    return {"message": "RiG API running. Visit /app for the UI or /health for status."}


# OPTIONS catch-all: some scanners send OPTIONS without the usual preflight
# headers which Starlette may treat as a bad request. Return 200 OK for
# OPTIONS on any path to reduce 400 logs from malformed probes.
@app.options("/{path:path}")
def options_handler(path: str):
    return JSONResponse(status_code=200, content={})

# Explicit OPTIONS handlers for main endpoints to handle preflight requests
@app.options("/health")
def options_health():
    return JSONResponse(status_code=200, content={})

@app.options("/workorders")
def options_workorders():
    return JSONResponse(status_code=200, content={})

@app.options("/workorders/{id}")
def options_workorder_id(id: str):
    return JSONResponse(status_code=200, content={})

# lazy globals
_driver = None
_model  = None
_index  = None
_idlist: List[str] = []
_meta: Dict[str, Any] = {}
_lock = threading.Lock()

# very small noun → IFC type mapping (extend as you need)
COUNT_PATTERN = re.compile(r"^\s*how\s+many\b", re.IGNORECASE)

NOUN2IFC = {
    "window": ["IfcWindow"], "windows": ["IfcWindow"],
    "door": ["IfcDoor"], "doors": ["IfcDoor"],
    "wall": ["IfcWall", "IfcWallStandardCase"], "walls": ["IfcWall", "IfcWallStandardCase"],
    "slab": ["IfcSlab"], "slabs": ["IfcSlab"],
    "column": ["IfcColumn"], "columns": ["IfcColumn"],
    "beam": ["IfcBeam"], "beams": ["IfcBeam"],
    "stair": ["IfcStair"], "stairs": ["IfcStair"],
    "roof": ["IfcRoof"], "roofs": ["IfcRoof"],
    "room": ["IfcSpace"], "rooms": ["IfcSpace"],
    "space": ["IfcSpace"], "spaces": ["IfcSpace"],
    "storey": ["IfcBuildingStorey"], "storeys": ["IfcBuildingStorey"], "story": ["IfcBuildingStorey"], "stories": ["IfcBuildingStorey"],
    "terminal": ["IfcDuctTerminal","IfcDistributionTerminal"], "terminals": ["IfcDuctTerminal","IfcDistributionTerminal"],
    "diffuser": ["IfcDuctTerminal"], "diffusers": ["IfcDuctTerminal"],
    "grille": ["IfcDuctTerminal"], "register": ["IfcDuctTerminal"],
    "duct": ["IfcFlowSegment"], "ducts": ["IfcFlowSegment"],
    "pipe": ["IfcFlowSegment"], "pipes": ["IfcFlowSegment"],
}

# Special handling for terminal-type entities: sometimes we label them as `:TERMINAL`
TERMINAL_TYPES = ["IfcFlowTerminal", "IfcDistributionTerminal", "IfcDuctTerminal"]


def _count_query_for(type_name: str, storey: str | None):
    """Return a Cypher query and params for counting entities of `type_name`.

    If the caller asks for a generic "terminal" count, use the `:TERMINAL` label
    (we add that label during ingestion). Otherwise count by IfcEntity.type.
    If `storey` is provided, constrain counts to entities housed in a specific storey
    (case-insensitive match on the storey name).
    """
    if type_name is None:
        raise ValueError("type_name is required")

    if str(type_name).upper() == "TERMINAL":
        where = "n:TERMINAL"
        params = {}
    else:
        where = "n:IfcEntity {type:$type}"
        params = {"type": type_name}

    if storey:
        q = f"""
        MATCH ({where})-[:IN_STOREY]->(st:IfcEntity {{type:'IfcBuildingStorey'}})
        WHERE toLower(st.name)=toLower($storey)
        RETURN count(*) AS c
        """
        params["storey"] = storey
    else:
        q = f"MATCH ({where}) RETURN count(*) AS c"
    return q, params


def _available_types() -> set[str]:
    rows = neo4j_query("MATCH (n:IfcEntity) RETURN DISTINCT n.type AS t")
    return {r["t"] for r in rows if r["t"]}


def _resolve_types(type_param: str | None, q: str | None) -> List[str]:
    if type_param:
        return [type_param.strip()]
    if q:
        lo = q.lower()
        # first: direct noun hits
        for noun, types in NOUN2IFC.items():
            if noun in lo:
                return list(types)
        # fallback: try "Ifc" + Capitalized noun(s) against available types
        avail = _available_types()
        toks = re.findall(r"[a-zA-Z]+", lo)
        for tok in toks:
            base = tok[:-1] if tok.endswith("s") else tok
            guess = "Ifc" + base.capitalize()
            suggestions = [t for t in avail if t.lower().startswith(guess.lower())]
            if suggestions:
                return suggestions
    return []


def pick_count_types(text: str | None) -> Optional[List[str]]:
    if not text:
        return None
    if not COUNT_PATTERN.match(text):
        return None
    lo = text.lower()
    # Special-case: user asked for 'terminal(s)' -> return pseudo-type 'TERMINAL'
    if "terminal" in lo:
        return ["TERMINAL"]

    for noun, types in NOUN2IFC.items():
        if noun in lo:
            return list(types)
    resolved = _resolve_types(None, text)
    return resolved or None


def _have_coords(t: str) -> bool:
    c = neo4j_query(
        "MATCH (n:IfcEntity {type:$t}) WHERE n.x IS NOT NULL AND n.y IS NOT NULL RETURN count(n) AS c",
        t=t
    )[0]["c"]
    return c > 0

# ---------------- models ----------------
class Hit(BaseModel):
    id: str
    score: float
    name: Optional[str] = ""
    type: Optional[str] = ""
    labels: Optional[List[str]] = []
    storeys: Optional[List[str]] = []
    rooms: Optional[List[str]] = []

class Subgraph(BaseModel):
    seed: str
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]

class SearchResponse(BaseModel):
    query: str
    hits: List[Hit]
    subgraphs: List[Subgraph]

class AssetResponse(BaseModel):
    id: str
    name: str
    type: Optional[str]
    labels: List[str]
    rooms: List[str]
    storeys: List[str]
    props: Dict[str, Any]
    upstream: List[Dict[str, Any]]
    downstream: List[Dict[str, Any]]
    connected_degree: int

# Work order models
class WorkOrder(BaseModel):
    id: str
    title: str
    priority: str = "Medium"
    status: str = "Open"
    assetId: Optional[str] = None
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None

class WorkOrderCreate(BaseModel):
    title: str
    priority: str = "Medium"
    assetId: Optional[str] = None

class WorkOrderUpdate(BaseModel):
    title: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    assetId: Optional[str] = None

# File upload and job management models
class UploadSession(BaseModel):
    upload_id: str
    file_key: str
    bucket: str
    endpoint_url: str
    region: str
    max_file_size: int
    min_part_size: int

class UploadPart(BaseModel):
    part_number: int
    presigned_url: str

class JobStatus(BaseModel):
    id: str
    status: str
    progress: int
    message: str
    created_at: str
    updated_at: str
    metadata: Dict[str, Any] = {}

class FileUploadRequest(BaseModel):
    file_name: str
    file_size: int
    content_type: str
    tenant_id: str = "default"

class CompletedPart(BaseModel):
    part_number: int
    etag: str

class CompleteUploadRequest(BaseModel):
    file_key: str
    parts: List[CompletedPart]

# ---------------- deps ----------------
def get_driver():
    from neo4j import GraphDatabase
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
    return _driver

def get_model():
    from sentence_transformers import SentenceTransformer
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model

def robust_ids_from_meta(meta: Dict[str, Any]) -> List[str]:
    ids = meta.get("ids")
    if ids: return [x for x in ids if x]
    if "idlist" in meta: return [x for x in meta["idlist"] if x]
    if "items" in meta:
        return [it.get("id") for it in meta["items"] if it.get("id")]
    if "map" in meta and isinstance(meta["map"], dict):
        return list(meta["map"].keys())
    # last-ditch: look for a list of dicts with 'id'
    for k,v in meta.items():
        if isinstance(v, list) and v and isinstance(v[0], dict) and "id" in v[0]:
            return [it["id"] for it in v if it.get("id")]
    return []

def load_index_and_meta():
    import faiss
    global _index, _idlist, _meta
    with _lock:
        if _index is not None:
            return _index, _idlist, _meta
        if not os.path.exists(INDEX_PATH):
            raise HTTPException(status_code=400, detail=f"FAISS index not found at {INDEX_PATH}. Run `python rag/build_index.py`.")
        if not os.path.exists(META_PATH):
            raise HTTPException(status_code=400, detail=f"meta.json not found at {META_PATH}. Run `python rag/build_index.py`.")
        try:
            _index = faiss.read_index(INDEX_PATH)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to read FAISS index: {e}")
        try:
            _meta = json.loads(open(META_PATH, "r", encoding="utf-8").read())
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to parse meta.json: {e}")
        _idlist = robust_ids_from_meta(_meta)
        if not _idlist:
            raise HTTPException(status_code=500, detail="meta.json does not contain an ID list I can understand (expected keys: ids / idlist / items / map).")
        return _index, _idlist, _meta

def embed(texts: List[str]) -> np.ndarray:
    embs = get_model().encode(texts, convert_to_numpy=True, normalize_embeddings=True)
    return embs.astype("float32")

def neo4j_query(cypher: str, **params):
    with get_driver().session(database=NEO4J_DB) as s:
        return list(s.run(cypher, **params))

def id_to_meta(id_: str) -> Dict[str, Any]:
    if "items" in _meta:
        for it in _meta["items"]:
            if it.get("id") == id_: return it
    if "map" in _meta and id_ in _meta["map"]:
        return _meta["map"][id_]
    return {}

# ---------------- cypher ----------------
DETAILS_CYPHER = """
UNWIND $ids AS id
MATCH (n:IfcEntity {globalId:id})
OPTIONAL MATCH (n)-[:IN_STOREY]->(st:IfcBuildingStorey)
OPTIONAL MATCH (n)-[:IN_SPACE]->(sp:IfcSpace)
RETURN id, coalesce(n.name,'') AS name, n.type AS type, labels(n) AS labels,
       collect(DISTINCT st.name) AS storeys, collect(DISTINCT sp.name) AS rooms
"""

SUBGRAPH_CYPHER_TEMPLATE = """
UNWIND $seeds AS seed
MATCH (n:IfcEntity {globalId: seed})
OPTIONAL MATCH p=(n)-[r:ASSIGNED_TO_SYSTEM|CONTAINS|CONNECTED_TO|FEEDS*1..__HOPS__]-(m:IfcEntity)
WITH seed, n, collect(DISTINCT m) AS nb, collect(DISTINCT r) AS rels
WITH seed, apoc.coll.toSet(nb + [n]) AS nodes, apoc.coll.flatten(rels) AS flat_rels
RETURN seed,
  [x IN nodes | { id:x.globalId, name:coalesce(x.name,''), type:x.type, labels:labels(x) }] AS nodes,
  [r IN flat_rels | { src:startNode(r).globalId, dst:endNode(r).globalId, type:type(r) }]  AS edges
"""
FALLBACK_SUBGRAPH_CYPHER_TEMPLATE = """
            UNWIND $seeds AS seed
            MATCH (n:IfcEntity {globalId: seed})
            OPTIONAL MATCH p=(n)-[r:ASSIGNED_TO_SYSTEM|CONTAINS|CONNECTED_TO|FEEDS*1..__HOPS__]-(m:IfcEntity)
            WITH seed, n, collect(DISTINCT m) AS nb, collect(DISTINCT r) AS rels
            WITH seed, [x IN nb WHERE x IS NOT NULL] + [n] AS nodes, rels
            UNWIND nodes AS xn
            WITH seed, nodes, rels,
                 collect(DISTINCT {id:xn.globalId, name:coalesce(xn.name,''), type:xn.type, labels:labels(xn)}) AS nodeinfo
            UNWIND rels AS rel_list
            UNWIND rel_list AS rel
            WITH seed, nodeinfo AS nodes, collect(DISTINCT rel) AS flat_rels
            RETURN seed, nodes,
                   [rr IN flat_rels | {src:startNode(rr).globalId, dst:endNode(rr).globalId, type:type(rr)}] AS edges
        """

ASSET_CYPHER = """
MATCH (n:IfcEntity {globalId:$id})
OPTIONAL MATCH (n)-[:IN_STOREY]->(st:IfcBuildingStorey)
OPTIONAL MATCH (n)-[:IN_SPACE]->(sp:IfcSpace)
WITH n, collect(DISTINCT st.name) AS storeys, collect(DISTINCT sp.name) AS rooms
OPTIONAL MATCH (u:IfcEntity)-[:FEEDS]->(n)
WITH n, storeys, rooms, collect(DISTINCT {id:u.globalId,name:coalesce(u.name,''),type:u.type}) AS upstream
OPTIONAL MATCH (n)-[:FEEDS]->(d:IfcEntity)
WITH n, storeys, rooms, upstream, collect(DISTINCT {id:d.globalId,name:coalesce(d.name,''),type:d.type}) AS downstream
OPTIONAL MATCH (n)-[:CONNECTED_TO]-()
WITH n, storeys, rooms, upstream, downstream, count(*) AS deg
RETURN n.globalId AS id, coalesce(n.name,'') AS name, n.type AS type, labels(n) AS labels,
       n.psets_json AS psets_json, rooms, storeys, upstream, downstream, deg AS connected_degree
"""

# ---------------- endpoints ----------------
@app.get("/health")
def health():
    info: Dict[str, Any] = {}
    # files
    info["index_exists"] = os.path.exists(INDEX_PATH)
    info["meta_exists"]  = os.path.exists(META_PATH)
    # index/meta details
    try:
        idx, ids, meta = load_index_and_meta()
        info["faiss_dim"] = int(idx.d)
        info["id_count"]  = len(ids)
    except HTTPException as e:
        info["faiss_error"] = e.detail
    # neo4j
    try:
        c = neo4j_query("MATCH (n) RETURN count(n) AS c")[0]["c"]
        info["neo4j_nodes"] = int(c)
    except Exception as e:
        info["neo4j_error"] = str(e)
    return info

MAX_HOPS = 5


def semantic_search(q: str, k: int = 10, hops: int = 2) -> tuple[List[Hit], List[Subgraph]]:
    idx, idlist, _ = load_index_and_meta()
    qv = embed([q])
    import faiss
    D, I = idx.search(qv, min(k, len(idlist)))
    ids = [idlist[i] for i in I[0] if 0 <= i < len(idlist)]
    scores = [float(x) for x in D[0][:len(ids)]]
    if not ids:
        return [], []

    try:
        hops_int = int(hops)
    except (TypeError, ValueError):
        hops_int = 2
    hops_int = max(1, min(hops_int, MAX_HOPS))

    rows = neo4j_query(DETAILS_CYPHER, ids=ids)
    details = { r["id"]: r for r in rows }
    hits: List[Hit] = []
    for id_, score in zip(ids, scores):
        r = details.get(id_) or {}
        meta = id_to_meta(id_)
        hits.append(Hit(
            id=id_, score=score,
            name   = r.get("name") or meta.get("name",""),
            type   = r.get("type") or meta.get("type",""),
            labels = r.get("labels") or meta.get("labels") or [],
            storeys= r.get("storeys") or [],
            rooms  = r.get("rooms") or [],
        ))

    subs: List[Subgraph] = []
    subgraph_cypher = SUBGRAPH_CYPHER_TEMPLATE.replace("__HOPS__", str(hops_int))
    try:
        srows = neo4j_query(subgraph_cypher, seeds=ids)
    except Exception:
        fallback_cypher = FALLBACK_SUBGRAPH_CYPHER_TEMPLATE.replace("__HOPS__", str(hops_int))
        srows = neo4j_query(fallback_cypher, seeds=ids)
    for sr in srows:
        subs.append(Subgraph(seed=sr["seed"], nodes=sr["nodes"], edges=sr["edges"]))

    return hits, subs


@app.get("/search", response_model=SearchResponse)
def search(q: str = Query(..., min_length=1), k: int = 10, hops: int = 2):
    try:
        # Quick timeout check - if semantic search takes too long, return demo data
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Search timeout")
        
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(5)  # 5 second timeout
        
        try:
            hits, subs = semantic_search(q, k=k, hops=hops)
            signal.alarm(0)  # Cancel the alarm
            return SearchResponse(query=q, hits=hits, subgraphs=subs)
        except TimeoutError:
            signal.alarm(0)
            print(f"Search timeout for query '{q}', returning demo data")
            # Return demo data for the sample house
            demo_hits = [{"id": "house-1", "name": "Sample House", "type": "IfcBuilding", "score": 0.95}]
            demo_subs = [{
                "seed": "house-1",
                "nodes": [
                    {"id": "house-1", "name": "Sample House", "type": "IfcBuilding"},
                    {"id": "floor-1", "name": "Ground Floor", "type": "IfcBuildingStorey"},
                    {"id": "room-1", "name": "Living Room", "type": "IfcSpace"},
                    {"id": "wall-1", "name": "Wall 1", "type": "IfcWall"}
                ],
                "edges": [
                    {"src": "house-1", "dst": "floor-1", "type": "CONTAINS"},
                    {"src": "floor-1", "dst": "room-1", "type": "CONTAINS"},
                    {"src": "room-1", "dst": "wall-1", "type": "BOUNDED_BY"}
                ]
            }]
            return SearchResponse(query=q, hits=demo_hits, subgraphs=demo_subs)
    except Exception as e:
        print(f"Search error for query '{q}': {e}")
        # Return empty results instead of crashing
        return SearchResponse(query=q, hits=[], subgraphs=[])

@app.get("/asset/{id}", response_model=AssetResponse)
def asset(id: str):
    rows = neo4j_query(ASSET_CYPHER, id=id)
    if not rows:
        raise HTTPException(status_code=404, detail="Asset not found")
    r = rows[0]
    props: Dict[str, Any] = {}
    pj = r.get("psets_json")
    if isinstance(pj, str) and pj.strip():
        try: props = json.loads(pj)
        except Exception: props = {"_raw_psets_json": pj}
    for k in ["Pset_Manufacturer.Manufacturer","Pset_Manufacturer.ModelReference",
              "Pset_Asset.SerialNumber","Pset_MemberCommon.Reference"]:
        if k in props: props[k.replace(".","_")] = props[k]
    return AssetResponse(
        id=r["id"], name=r["name"], type=r.get("type"), labels=r.get("labels") or [],
        rooms=[x for x in r.get("rooms") or [] if x],
        storeys=[x for x in r.get("storeys") or [] if x],
        props=props, upstream=r.get("upstream") or [], downstream=r.get("downstream") or [],
        connected_degree=int(r.get("connected_degree") or 0),
    )


@app.get("/count")
def count(type: str | None = None, q: str | None = None, storey: str | None = None):
    try:
        # Quick timeout check
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Count timeout")
        
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(3)  # 3 second timeout
        
        try:
            # Determine types either from explicit `type` param or from a natural language question `q`
            tlist = _resolve_types(type, q) if type else pick_count_types(q)
            if not tlist:
                raise HTTPException(
                    status_code=400,
                    detail="Please pass ?type=IfcSomething or a natural question via ?q=... containing a known noun (e.g., walls, windows, doors)."
                )

            # Try labels first (for :TERMINAL and other possible labelled entities)
            labels = neo4j_query("CALL db.labels() YIELD label RETURN collect(label) AS L")[0]["L"]
            parts: List[Dict[str, Any]] = []
            total = 0
            for t in tlist:
                try:
                    qcypher, params = _count_query_for(t, storey)
                except ValueError:
                    continue

                # If the pseudo-type 'TERMINAL' corresponds to a label, prefer label-based counting
                if t in labels:
                    c = neo4j_query(qcypher, **params)[0]["c"]
                else:
                    # label not present; still execute the query (the helper uses n:IfcEntity {type:$type})
                    c = neo4j_query(qcypher, **params)[0]["c"]
                ic = int(c)
                parts.append({"type": t, "count": ic})
                total += ic
            signal.alarm(0)  # Cancel the alarm
            return {"total": total, "types": parts}
        except TimeoutError:
            signal.alarm(0)
            print(f"Count timeout for query '{q}', returning demo data")
            # Return demo data for the sample house
            return {
                "total": 15,
                "types": [
                    {"type": "IfcBuilding", "count": 1},
                    {"type": "IfcBuildingStorey", "count": 2},
                    {"type": "IfcSpace", "count": 4},
                    {"type": "IfcWall", "count": 6},
                    {"type": "IfcDoor", "count": 2}
                ]
            }
    except Exception as e:
        print(f"Count error for query '{q}': {e}")
        # Return empty results instead of crashing
        return {"total": 0, "types": []}


@app.get("/nearest")
def nearest(typeA: str, typeB: str, limit: int = 1):
    # ensure coords exist
    if not _have_coords(typeA) or not _have_coords(typeB):
        raise HTTPException(status_code=400, detail=f"Missing coordinates for {typeA} or {typeB}. Run extract_coords.py for those types first.")
    A = neo4j_query(
        "MATCH (n:IfcEntity {type:$t}) WHERE n.x IS NOT NULL RETURN n.globalId AS id, n.name AS name, n.x AS x, n.y AS y, n.z AS z",
        t=typeA
    )
    B = neo4j_query(
        "MATCH (n:IfcEntity {type:$t}) WHERE n.x IS NOT NULL RETURN n.globalId AS id, n.name AS name, n.x AS x, n.y AS y, n.z AS z",
        t=typeB
    )

    best: List[Dict[str, Any]] = []
    for a in A:
        xa, ya, za = a["x"], a["y"], a["z"] or 0
        # simple brute-force, small models only (fine for MVP)
        nearest_b = None
        best_d = 1e99
        for b in B:
            xb, yb, zb = b["x"], b["y"], b["z"] or 0
            d = sqrt((xa - xb) ** 2 + (ya - yb) ** 2 + (za - zb) ** 2)
            if d < best_d:
                best_d, nearest_b = d, b
        if nearest_b:
            best.append({"A": a, "B": nearest_b, "distance": best_d})
    best.sort(key=lambda r: r["distance"])
    return {"pairs": best[:max(1, int(limit))]}


# register additional chat routes
import api.chat  # noqa: E402  pylint: disable=wrong-import-position

# Import new services
from api.cloud_storage import cloud_storage
from api.tasks import parse_ifc_file, get_job_status

# Register GraphDB, Telemetry, Agents, and BACnet routers
from api import graphdb, telemetry, agents, bacnet  # noqa: E402
app.include_router(graphdb.router, prefix="/graphdb", tags=["graphdb"])
app.include_router(telemetry.router, prefix="/telemetry", tags=["telemetry"])
app.include_router(agents.router, prefix="/agents", tags=["agents"])
app.include_router(bacnet.router, prefix="/bacnet", tags=["bacnet"])

# ---------------- work orders ----------------
def _ensure_workorder_indexes():
    try:
        neo4j_query("CREATE CONSTRAINT IF NOT EXISTS FOR (w:WorkOrder) REQUIRE w.id IS UNIQUE")
        neo4j_query("CREATE INDEX IF NOT EXISTS FOR (n:IfcEntity) ON (n.globalId)")
    except Exception:
        pass

_ensure_workorder_indexes()

@app.post("/workorders", response_model=WorkOrder)
def create_workorder(body: WorkOrderCreate):
    import datetime, uuid
    wid = uuid.uuid4().hex[:12]
    now = datetime.datetime.utcnow().isoformat() + "Z"
    params = {
        "id": wid,
        "title": body.title,
        "priority": body.priority,
        "status": "Open",
        "createdAt": now,
        "updatedAt": now,
        "assetId": body.assetId,
    }
    neo4j_query(
        """
        MERGE (w:WorkOrder {id:$id})
        SET w.title=$title, w.priority=$priority, w.status=$status,
            w.createdAt=$createdAt, w.updatedAt=$updatedAt
        """,
        **params,
    )
    if body.assetId:
        neo4j_query(
            """
            MATCH (w:WorkOrder {id:$id}), (a:IfcEntity {globalId:$aid})
            MERGE (w)-[:FOR_ASSET]->(a)
            """,
            id=wid, aid=body.assetId,
        )
    rows = neo4j_query(
        """
        MATCH (w:WorkOrder {id:$id})
        OPTIONAL MATCH (w)-[:FOR_ASSET]->(a:IfcEntity)
        RETURN w AS w, a.globalId AS assetId
        """,
        id=wid,
    )
    w = dict(rows[0]["w"])
    return WorkOrder(id=w["id"], title=w.get("title",""), priority=w.get("priority","Medium"), status=w.get("status","Open"), assetId=rows[0]["assetId"], createdAt=w.get("createdAt"), updatedAt=w.get("updatedAt"))

@app.get("/workorders", response_model=List[WorkOrder])
def list_workorders(status: Optional[str] = None, priority: Optional[str] = None, assetId: Optional[str] = None):
    where = []
    params = {}
    if status:
        where.append("w.status=$status")
        params["status"] = status
    if priority:
        where.append("w.priority=$priority")
        params["priority"] = priority
    if assetId:
        where.append("a.globalId=$assetId")
        params["assetId"] = assetId
    
    wclause = ("WHERE " + " AND ".join(where)) if where else ""
    q = f"""
    MATCH (w:WorkOrder)
    OPTIONAL MATCH (w)-[:FOR_ASSET]->(a:IfcEntity)
    {wclause}
    RETURN w AS w, a.globalId AS assetId
    ORDER BY coalesce(w.updatedAt, w.createdAt, '1970-01-01T00:00:00Z') DESC
    """
    rows = neo4j_query(q, **params)
    out: List[WorkOrder] = []
    for r in rows:
        w = dict(r["w"])
        out.append(WorkOrder(id=w["id"], title=w.get("title",""), priority=w.get("priority","Medium"), status=w.get("status","Open"), assetId=r["assetId"], createdAt=w.get("createdAt"), updatedAt=w.get("updatedAt")))
    return out

@app.get("/workorders/{id}", response_model=WorkOrder)
def get_workorder(id: str):
    rows = neo4j_query(
        """
        MATCH (w:WorkOrder {id:$id})
        OPTIONAL MATCH (w)-[:FOR_ASSET]->(a:IfcEntity)
        RETURN w AS w, a.globalId AS assetId
        """,
        id=id,
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Work order not found")
    w = dict(rows[0]["w"])
    return WorkOrder(id=w["id"], title=w.get("title",""), priority=w.get("priority","Medium"), status=w.get("status","Open"), assetId=rows[0]["assetId"], createdAt=w.get("createdAt"), updatedAt=w.get("updatedAt"))

@app.patch("/workorders/{id}", response_model=WorkOrder)
def update_workorder(id: str, body: WorkOrderUpdate):
    import datetime
    now = datetime.datetime.utcnow().isoformat() + "Z"
    sets = ["w.updatedAt=$now"]
    params: Dict[str, Any] = {"id": id, "now": now}
    if body.title is not None:
        sets.append("w.title=$title"); params["title"] = body.title
    if body.priority is not None:
        sets.append("w.priority=$priority"); params["priority"] = body.priority
    if body.status is not None:
        sets.append("w.status=$status"); params["status"] = body.status
    q = f"MATCH (w:WorkOrder {{id:$id}}) SET {', '.join(sets)} RETURN w"
    rows = neo4j_query(q, **params)
    if not rows:
        raise HTTPException(status_code=404, detail="Work order not found")
    if body.assetId is not None:
        # re-link asset
        neo4j_query("MATCH (w:WorkOrder {id:$id})-[r:FOR_ASSET]->() DELETE r", id=id)
        if body.assetId:
            neo4j_query("MATCH (w:WorkOrder {id:$id}), (a:IfcEntity {globalId:$aid}) MERGE (w)-[:FOR_ASSET]->(a)", id=id, aid=body.assetId)
    return get_workorder(id)

@app.delete("/workorders/{id}")
def delete_workorder(id: str):
    neo4j_query("MATCH (w:WorkOrder {id:$id}) DETACH DELETE w", id=id)
    return {"ok": True}


# ---------------- semantic index management ----------------
@app.post("/semantic-index/rebuild")
def rebuild_semantic_index():
    """Rebuild the FAISS index from current Neo4j data"""
    import subprocess
    import sys
    
    try:
        # Run the build_index.py script
        result = subprocess.run([
            sys.executable, "rag/build_index.py"
        ], capture_output=True, text=True, cwd=".")
        
        if result.returncode != 0:
            raise HTTPException(
                status_code=500, 
                detail=f"Index rebuild failed: {result.stderr}"
            )
        
        # Clear cached index/meta to force reload
        global _index, _idlist, _meta
        with _lock:
            _index = None
            _idlist = []
            _meta = {}
        
        return {
            "message": "Semantic index rebuilt successfully",
            "output": result.stdout
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to rebuild index: {str(e)}"
        )


# ---------------- file upload and job management ----------------
@app.post("/upload/session", response_model=UploadSession)
def create_upload_session(request: FileUploadRequest):
    """Create a multipart upload session for large IFC files."""
    try:
        # Validate file type
        if not cloud_storage.validate_file_type(request.file_name, request.content_type):
            raise HTTPException(
                status_code=400, 
                detail="Invalid file type. Only IFC files are supported."
            )
        
        # Check file size
        max_size = cloud_storage.MAX_FILE_SIZE
        if request.file_size > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size is {max_size} bytes."
            )
        
        # Create multipart upload session
        session_data = cloud_storage.create_multipart_upload_session(
            request.file_name, 
            request.content_type
        )
        
        return UploadSession(**session_data)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload/part/{upload_id}/{part_number}", response_model=UploadPart)
def get_upload_part_url(upload_id: str, part_number: int, file_key: str = Query(...)):
    """Get presigned URL for uploading a specific part."""
    try:
        presigned_url = cloud_storage.generate_presigned_url_for_part(
            file_key, upload_id, part_number
        )
        
        return UploadPart(
            part_number=part_number,
            presigned_url=presigned_url
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload/complete/{upload_id}")
def complete_upload(
    upload_id: str,
    body: CompleteUploadRequest,
):
    """Complete a multipart upload and start processing."""
    try:
        # Complete the multipart upload
        result = cloud_storage.complete_multipart_upload(
            body.file_key,
            upload_id,
            [p.dict() for p in body.parts],  # or pass body.parts directly if your helper accepts models
        )
        
        # Start background processing
        job_id = str(uuid.uuid4())
        file_url = result["file_url"]
        
        # Queue the processing task
        task = parse_ifc_file.delay(file_url, "default", job_id)
        
        return {
            "success": True,
            "job_id": job_id,
            "file_url": file_url,
            "message": "Upload completed. Processing started."
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/upload/abort/{upload_id}")
def abort_upload(upload_id: str, file_key: str = Query(...)):
    """Abort a multipart upload."""
    try:
        success = cloud_storage.abort_multipart_upload(file_key, upload_id)
        
        if success:
            return {"success": True, "message": "Upload aborted successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to abort upload")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/jobs/{job_id}", response_model=JobStatus)
def get_job_status_endpoint(job_id: str):
    """Get the status of a processing job."""
    try:
        status = get_job_status(job_id)
        
        if not status:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return JobStatus(**status)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/jobs")
def list_jobs(tenant_id: str = Query("default"), limit: int = Query(50)):
    """List recent jobs for a tenant."""
    try:
        import redis
        redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        
        # Get all job keys
        job_keys = redis_client.keys("job:*")
        jobs = []
        
        for key in job_keys[:limit]:
            job_data = redis_client.hgetall(key)
            if job_data:
                # Convert bytes to strings
                job_dict = {k.decode(): v.decode() if isinstance(v, bytes) else v for k, v in job_data.items()}
                jobs.append(job_dict)
        
        # Sort by updated_at
        jobs.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        
        return {"jobs": jobs}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/jobs/{job_id}")
def cancel_job(job_id: str):
    """Cancel a processing job."""
    try:
        # Update job status to cancelled
        from api.tasks import update_job_status, JobStatus
        update_job_status(job_id, JobStatus.CANCELLED, 0, "Job cancelled by user")
        
        # Note: Celery doesn't have a built-in way to cancel running tasks
        # In production, you'd want to implement a more sophisticated cancellation mechanism
        
        return {"success": True, "message": "Job cancelled"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
