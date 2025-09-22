import React, { useCallback, useEffect, useRef, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Database, Network, Send, Plus, FileUp, CheckCircle2, Factory, Wrench, MessageSquare, GitBranch } from "lucide-react";
import ForceGraph2D from "react-force-graph-2d";
import { API_BASE } from "@/lib/env";

// === Tiny helpers ===
const api = (p) => `${API_BASE}${p}`;
const pill = (ok) => (ok ? "bg-emerald-100 text-emerald-700" : "bg-rose-100 text-rose-700");
const DEFAULT_IFC_URL = "/ifc/sample-house.ifc";

// Minimal message bubble
function ChatBubble({ role, text }) {
  const isUser = role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-snug shadow-sm ${isUser ? "bg-emerald-600 text-white" : "bg-slate-100 text-slate-900"}`}
      >
        {text}
      </div>
    </div>
  );
}

// Work orders kept in localStorage for the MVP
function useLocalOrders() {
  const [orders, setOrders] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem("rig_orders") || "[]");
    } catch (err) {
      console.warn("Failed to parse cached work orders", err);
      return [];
    }
  });

  useEffect(() => {
    localStorage.setItem("rig_orders", JSON.stringify(orders));
  }, [orders]);

  return [orders, setOrders];
}

const COUNT_LEXICON = {
  window: ["IfcWindow"],
  windows: ["IfcWindow"],
  door: ["IfcDoor"],
  doors: ["IfcDoor"],
  wall: ["IfcWall", "IfcWallStandardCase"],
  walls: ["IfcWall", "IfcWallStandardCase"],
  terminal: ["IfcDuctTerminal", "IfcDistributionTerminal"],
  terminals: ["IfcDuctTerminal", "IfcDistributionTerminal"],
  diffuser: ["IfcDuctTerminal"],
  diffusers: ["IfcDuctTerminal"],
};

export default function FacilityTwin_MVP_UI() {
  // Health/Status
  const [health, setHealth] = useState(null);
  const [busy, setBusy] = useState(false);

  // IFC viewer
  const ifcContainerRef = useRef(null);
  const viewerRef = useRef(null);
  const fileInputRef = useRef(null);
  const defaultIfcLoadedRef = useRef(false);
  const bootstrappedSearchRef = useRef(false);

  // Search / chat
  const [q, setQ] = useState("Which terminals are downstream of Apparecchiatura 2881?");
  const [k, setK] = useState(10);
  const [hops, setHops] = useState(2);
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      text: "Hi! Ask about the model, e.g. count windows, find downstream terminals, or fetch an asset.",
    },
  ]);
  const addMsg = useCallback((m) => setMessages((prev) => [...prev, m]), []);

  // Hits / Asset details
  const [hits, setHits] = useState([]);
  const [asset, setAsset] = useState(null);

  // Graph
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });

  // Work orders
  const [orders, setOrders] = useLocalOrders();
  const [woDraft, setWoDraft] = useState({ title: "", priority: "Medium", assetId: "" });

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(api("/health"));
        const h = await res.json();
        setHealth(h);
      } catch (e) {
        setHealth({ error: String(e) });
      }
    })();
  }, []);

  const fetchAsset = useCallback(async (id) => {
    const res = await fetch(api(`/asset/${encodeURIComponent(id)}`));
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || JSON.stringify(data));
    return data;
  }, []);

  const openAsset = useCallback(
    async (id) => {
      try {
        const data = await fetchAsset(id);
        setAsset(data);
        setWoDraft((prev) => ({ ...prev, assetId: id }));
        addMsg({ role: "assistant", text: `Loaded asset ${id}` });
      } catch (e) {
        addMsg({ role: "assistant", text: `Error loading asset: ${String(e.message || e)}` });
      }
    },
    [addMsg, fetchAsset]
  );

  const onIfcFile = useCallback(
    async (file) => {
      if (!viewerRef.current) {
        alert("IFC viewer not available in this environment");
        return;
      }
      setBusy(true);
      try {
        await viewerRef.current.IFC.loadIfc(file, true);
        defaultIfcLoadedRef.current = true;
        addMsg({ role: "assistant", text: `Loaded IFC: ${file.name}` });
      } finally {
        setBusy(false);
      }
    },
    [addMsg]
  );

  const pickCountTypes = useCallback((text) => {
    const lo = text.toLowerCase();
    if (!/^how\s+many\b/.test(lo)) return null;
    for (const key of Object.keys(COUNT_LEXICON)) {
      if (lo.includes(key)) return COUNT_LEXICON[key];
    }
    return null;
  }, []);

  const runQuery = useCallback(async () => {
    const text = q.trim();
    if (!text) return;

    addMsg({ role: "user", text });

    const countTypes = pickCountTypes(text);
    setBusy(true);

    try {
      if (countTypes) {
        const parts = [];
        let total = 0;
        for (const t of countTypes) {
          const r = await fetch(api(`/count?type=${encodeURIComponent(t)}`));
          const d = await r.json();
          if (!r.ok) throw new Error(d.detail || d.error || JSON.stringify(d));
          const c = d.total ?? d.count ?? 0;
          parts.push(`${t}: ${c}`);
          total += c;
        }
        addMsg({ role: "assistant", text: `Total ${total} (${parts.join(", ")})` });
        setHits([]);
        setGraphData({ nodes: [], links: [] });
        setAsset(null);
        return;
      }

      const res = await fetch(api(`/search?q=${encodeURIComponent(text)}&k=${k}&hops=${hops}`));
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || JSON.stringify(data));

      setHits(data.hits || []);

      const nodes = [];
      const links = [];
      const seen = new Set();
      (data.subgraphs || []).forEach((sg) => {
        (sg.nodes || []).forEach((n) => {
          if (seen.has(n.id)) return;
          seen.add(n.id);
          nodes.push({
            id: n.id,
            name: n.name || "(unnamed)",
            type: n.type || "",
            source: n.source || "",
          });
        });
        (sg.edges || []).forEach((e) => {
          links.push({ source: e.src, target: e.dst, type: e.type });
        });
      });

      const degree = {};
      links.forEach((edge) => {
        if (edge.source) degree[edge.source] = (degree[edge.source] || 0) + 1;
        if (edge.target) degree[edge.target] = (degree[edge.target] || 0) + 1;
      });
      const enrichedNodes = nodes.map((n) => ({ ...n, degree: degree[n.id] || 0 }));

      setGraphData({ nodes: enrichedNodes, links });
      addMsg({
        role: "assistant",
        text: `Found ${data.hits?.length || 0} hits; expanded ${data.subgraphs?.length || 0} neighborhoods.`,
      });

      const primary = data.hits?.[0]?.id || enrichedNodes[0]?.id;
      if (primary) await openAsset(primary);
    } catch (e) {
      console.error(e);
      addMsg({ role: "assistant", text: `Error: ${String(e.message || e)}` });
    } finally {
      setBusy(false);
    }
  }, [addMsg, k, hops, openAsset, pickCountTypes, q]);

  useEffect(() => {
    if (!health || health.error || bootstrappedSearchRef.current) return;
    if (!health.neo4j_nodes && !health.index_exists) return;
    bootstrappedSearchRef.current = true;
    runQuery();
  }, [health, runQuery]);

  useEffect(() => {
    let cancelled = false;

    async function initViewer() {
      if (!ifcContainerRef.current || viewerRef.current) return;

      try {
        const [{ IfcViewerAPI }, three] = await Promise.all([
          import("web-ifc-viewer").catch(() => null),
          import("three").catch(() => null),
        ]);

        if (cancelled || !IfcViewerAPI || !three) return;

        const viewer = new IfcViewerAPI({
          container: ifcContainerRef.current,
          backgroundColor: new three.Color(0xf8fafc),
        });

        viewer.axes.setAxes();
        viewer.grid.setGrid();
        viewer.IFC.setWasmPath("/ifc/");
        viewerRef.current = viewer;

        if (!defaultIfcLoadedRef.current) {
          try {
            const response = await fetch(DEFAULT_IFC_URL);
            if (cancelled || !response.ok) return;
            const blob = await response.blob();
            const filename = DEFAULT_IFC_URL.split("/").pop() || "model.ifc";
            const file = new File([blob], filename, {
              type: blob.type || "application/octet-stream",
            });
            await viewer.IFC.loadIfc(file, true);
            defaultIfcLoadedRef.current = true;
            if (!cancelled) {
              addMsg({ role: "assistant", text: `Loaded default IFC model (${filename}).` });
            }
          } catch (err) {
            if (!cancelled) console.warn("Failed to preload default IFC", err);
          }
        }
      } catch (err) {
        if (!cancelled) console.warn("IFC viewer failed to init", err);
      }
    }

    initViewer();

    return () => {
      cancelled = true;
      viewerRef.current?.dispose?.();
      viewerRef.current = null;
    };
  }, [addMsg]);

  const drawNode = useCallback((node, ctx, scale) => {
    const radius = 4 + Math.log((node.degree || 1) + 1) * 2;
    ctx.beginPath();
    ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI, false);
    ctx.fillStyle = node.type?.startsWith("IfcFlow")
      ? "#0ea5e9"
      : node.type?.startsWith("IfcSpace")
      ? "#22c55e"
      : "#cbd5e1";
    ctx.fill();
    ctx.font = `${Math.max(10 / scale, 8)}px Inter, system-ui`;
    ctx.fillStyle = "#0f172a";
    const label = node.name?.slice(0, 42) || node.id;
    ctx.fillText(label, node.x + radius + 3, node.y + 3);
  }, []);

  return (
    <div className="min-h-screen bg-slate-100 text-slate-900">
      <div className="mx-auto max-w-7xl space-y-5 p-6">
        <header className="flex flex-wrap items-center gap-3 rounded-2xl border border-slate-200 bg-white px-5 py-4 shadow-sm">
          <Factory className="h-6 w-6" />
          <h1 className="text-xl font-semibold">RiG – Facility Twin MVP</h1>
          <Badge className="ml-1">GraphRAG + IFC</Badge>
          <div className="ml-auto flex flex-wrap items-center gap-2 text-xs">
            <Badge className={pill(!!health)}>
              <Database className="mr-1 h-3 w-3" /> API
            </Badge>
            <Badge className={pill(!!(health && health.neo4j_nodes))}>
              <Network className="mr-1 h-3 w-3" /> {health?.neo4j_nodes ?? 0} nodes
            </Badge>
            <Badge className={pill(!!(health && health.index_exists))}>
              <GitBranch className="mr-1 h-3 w-3" /> index
            </Badge>
          </div>
        </header>

        <div className="grid gap-5 xl:grid-cols-3">
          <div className="space-y-5">
            <Card className="h-[420px] border-slate-200 shadow-sm">
              <CardHeader className="py-3">
                <CardTitle className="flex items-center justify-between text-base">
                  <span>IFC Geometry Viewer</span>
                  <div className="flex items-center gap-2 text-xs font-medium">
                    <FileUp className="h-4 w-4" />
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".ifc,.ifczip"
                      className="hidden"
                      onChange={(e) => {
                        const file = e.target.files?.[0];
                        if (file) onIfcFile(file);
                      }}
                    />
                    <Button variant="outline" size="sm" onClick={() => fileInputRef.current?.click()}>
                      Load IFC
                    </Button>
                  </div>
                </CardTitle>
              </CardHeader>
              <CardContent className="h-[350px] p-0">
                <div ref={ifcContainerRef} className="h-full w-full rounded-b-2xl bg-slate-50" />
              </CardContent>
            </Card>

            <Card className="h-[360px] border-slate-200 shadow-sm">
              <CardHeader className="py-3">
                <CardTitle className="flex items-center gap-2 text-base">
                  <MessageSquare className="h-4 w-4" /> Ask the model
                </CardTitle>
              </CardHeader>
              <CardContent className="flex h-[290px] flex-col gap-3">
                <div className="flex-1 overflow-hidden rounded-xl border border-slate-200 bg-white/80 p-3">
                  <div className="flex h-full flex-col gap-2 overflow-auto pr-1">
                    {messages.map((m, i) => (
                      <ChatBubble key={i} role={m.role} text={m.text} />
                    ))}
                  </div>
                </div>
                <div className="grid gap-2 md:grid-cols-[minmax(0,1fr)_auto_auto_auto_auto] md:items-end">
                  <div className="space-y-1">
                    <Label htmlFor="rig-query" className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                      Question
                    </Label>
                    <Input
                      id="rig-query"
                      className="bg-white"
                      value={q}
                      onChange={(e) => setQ(e.target.value)}
                      placeholder="e.g., how many windows are there?"
                    />
                  </div>
                  <div className="space-y-1">
                    <Label htmlFor="rig-k" className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                      Top-k
                    </Label>
                    <Input
                      id="rig-k"
                      type="number"
                      inputMode="numeric"
                      min={1}
                      max={50}
                      className="w-20 bg-white text-center"
                      value={k}
                      onChange={(e) => setK(Math.max(1, Number(e.target.value) || 10))}
                    />
                  </div>
                  <div className="space-y-1">
                    <Label htmlFor="rig-hops" className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                      Hops
                    </Label>
                    <Input
                      id="rig-hops"
                      type="number"
                      inputMode="numeric"
                      min={1}
                      max={5}
                      className="w-20 bg-white text-center"
                      value={hops}
                      onChange={(e) => setHops(Math.max(1, Number(e.target.value) || 2))}
                    />
                  </div>
                  <Button className="h-10 md:ml-2" onClick={runQuery} disabled={busy}>
                    <Send className="mr-1 h-4 w-4" />
                    {busy ? "Working…" : "Send"}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="space-y-5">
            <Card className="h-[420px] border-slate-200 shadow-sm">
              <CardHeader className="py-3">
                <CardTitle className="flex items-center gap-2 text-base">
                  <Network className="h-4 w-4" /> Model Graph
                </CardTitle>
              </CardHeader>
              <CardContent className="h-[350px] rounded-b-2xl bg-white p-0">
                <ForceGraph2D
                  graphData={graphData}
                  nodeId="id"
                  nodeCanvasObject={drawNode}
                  linkDirectionalArrowLength={4}
                  linkColor={() => "#94a3b8"}
                  onNodeClick={(n) => openAsset(n.id)}
                />
              </CardContent>
            </Card>

            <Card className="h-[360px] border-slate-200 shadow-sm">
              <CardHeader className="py-3">
                <CardTitle className="text-base">Hits</CardTitle>
              </CardHeader>
              <CardContent className="h-[290px] space-y-2 overflow-auto">
                {!hits.length && <div className="text-sm text-slate-500">No results yet.</div>}
                {hits.map((h, i) => (
                  <button
                    key={i}
                    type="button"
                    className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-left shadow-sm transition hover:border-emerald-300 hover:bg-emerald-50"
                    onClick={() => openAsset(h.id)}
                  >
                    <div className="font-medium">{h.name || "(unnamed)"}</div>
                    <div className="text-xs text-slate-500">{h.id}</div>
                    <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
                      <Badge variant="outline">{h.type}</Badge>
                      {h.rooms?.length ? <Badge variant="secondary">rooms: {h.rooms.join(", ")}</Badge> : null}
                      {h.storeys?.length ? <Badge variant="secondary">storeys: {h.storeys.join(", ")}</Badge> : null}
                      {typeof h.score === "number" && (
                        <span className="ml-auto text-slate-400">score {h.score.toFixed(3)}</span>
                      )}
                    </div>
                  </button>
                ))}
              </CardContent>
            </Card>
          </div>

          <div className="space-y-5">
            <Card className="h-[420px] border-slate-200 shadow-sm">
              <CardHeader className="py-3">
                <CardTitle className="text-base">Asset Details</CardTitle>
              </CardHeader>
              <CardContent className="h-[350px] space-y-3 overflow-auto">
                {!asset && <div className="text-sm text-slate-500">Click a node or a hit to load details…</div>}
                {asset && (
                  <div className="space-y-3">
                    <div className="text-xs text-slate-400">{asset.id}</div>
                    <div className="text-lg font-semibold leading-tight">{asset.name || "(unnamed asset)"}</div>
                    <div className="flex flex-wrap items-center gap-2 text-xs">
                      <Badge variant="outline">{asset.type}</Badge>
                      {asset.source && <Badge variant="secondary">{asset.source}</Badge>}
                    </div>
                    <div className="grid grid-cols-3 gap-2 text-sm">
                      {asset.x !== undefined && (
                        <div className="rounded-lg bg-slate-100 px-2 py-1">
                          <div className="text-xs uppercase text-slate-500">coord.x</div>
                          <div className="font-mono text-sm">{Math.round(asset.x)}</div>
                        </div>
                      )}
                      {asset.y !== undefined && (
                        <div className="rounded-lg bg-slate-100 px-2 py-1">
                          <div className="text-xs uppercase text-slate-500">coord.y</div>
                          <div className="font-mono text-sm">{Math.round(asset.y)}</div>
                        </div>
                      )}
                      {asset.z !== undefined && (
                        <div className="rounded-lg bg-slate-100 px-2 py-1">
                          <div className="text-xs uppercase text-slate-500">coord.z</div>
                          <div className="font-mono text-sm">{Math.round(asset.z)}</div>
                        </div>
                      )}
                    </div>
                    {asset.psets && (
                      <div>
                        <div className="text-sm font-medium">Property Sets</div>
                        <pre className="max-h-48 overflow-auto rounded-xl bg-slate-100 p-3 text-xs">
                          {JSON.stringify(asset.psets, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>

            <Card className="h-[360px] border-slate-200 shadow-sm">
              <CardHeader className="py-3">
                <CardTitle className="flex items-center gap-2 text-base">
                  <Wrench className="h-4 w-4" /> Work Orders
                </CardTitle>
              </CardHeader>
              <CardContent className="flex h-[290px] flex-col gap-3">
                <div className="grid grid-cols-6 items-end gap-2 text-xs">
                  <div className="col-span-3 space-y-1">
                    <Label className="text-xs font-semibold uppercase tracking-wide text-slate-500">Title</Label>
                    <Input
                      className="bg-white"
                      placeholder="title"
                      value={woDraft.title}
                      onChange={(e) => setWoDraft({ ...woDraft, title: e.target.value })}
                    />
                  </div>
                  <div className="col-span-1 space-y-1">
                    <Label className="text-xs font-semibold uppercase tracking-wide text-slate-500">Priority</Label>
                    <Select value={woDraft.priority} onValueChange={(v) => setWoDraft({ ...woDraft, priority: v })}>
                      <SelectTrigger className="bg-white">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Low">Low</SelectItem>
                        <SelectItem value="Medium">Medium</SelectItem>
                        <SelectItem value="High">High</SelectItem>
                        <SelectItem value="Critical">Critical</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="col-span-2 space-y-1">
                    <Label className="text-xs font-semibold uppercase tracking-wide text-slate-500">Asset ID</Label>
                    <Input
                      className="bg-white"
                      placeholder="asset id"
                      value={woDraft.assetId}
                      onChange={(e) => setWoDraft({ ...woDraft, assetId: e.target.value })}
                    />
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    onClick={() => {
                      if (!woDraft.title) return;
                      setOrders([{ id: Date.now().toString(36), status: "Open", ...woDraft }, ...orders]);
                      setWoDraft({ title: "", priority: "Medium", assetId: woDraft.assetId });
                    }}
                  >
                    <Plus className="mr-1 h-4 w-4" /> Add
                  </Button>
                  {asset && (
                    <Button variant="outline" size="sm" onClick={() => setWoDraft((w) => ({ ...w, assetId: asset.id }))}>
                      Use current asset
                    </Button>
                  )}
                </div>
                <div className="flex-1 space-y-2 overflow-auto">
                  {!orders.length && <div className="text-sm text-slate-500">No work orders.</div>}
                  {orders.map((o) => (
                    <div key={o.id} className="rounded-xl border border-slate-200 bg-white p-3 text-sm shadow-sm">
                      <div className="flex items-center gap-2">
                        <div className="font-medium">{o.title}</div>
                        <Badge variant={o.priority === "Critical" ? "destructive" : "secondary"}>{o.priority}</Badge>
                        {o.assetId && (
                          <Badge
                            variant="outline"
                            className="ml-auto cursor-pointer"
                            onClick={() => openAsset(o.assetId)}
                          >
                            {o.assetId}
                          </Badge>
                        )}
                      </div>
                      <div className="mt-2 flex items-center gap-2 text-xs">
                        <span className="text-slate-500">{o.status}</span>
                        <Button
                          size="xs"
                          variant="outline"
                          onClick={() =>
                            setOrders(orders.map((x) => (x.id === o.id ? { ...x, status: "Done" } : x)))
                          }
                        >
                          <CheckCircle2 className="mr-1 h-3 w-3" /> Mark done
                        </Button>
                        <Button size="xs" variant="ghost" onClick={() => setOrders(orders.filter((x) => x.id !== o.id))}>
                          Delete
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
