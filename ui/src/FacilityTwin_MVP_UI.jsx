import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Database, Network, Send, Plus, FileUp, CheckCircle2, Factory, Wrench, MessageSquare, GitBranch } from "lucide-react";
import ForceGraph2D from "react-force-graph-2d";
import { API_BASE } from "@/lib/env";
import { cn } from "@/lib/utils";

// === Tiny helpers ===
const api = (p) => `${API_BASE}${p}`;
const pill = (ok) => (ok ? "bg-emerald-100 text-emerald-700" : "bg-rose-100 text-rose-700");
const DEFAULT_IFC_URL = "/ifc/sample-house.ifc";

const FRIENDLY_TYPES = {
  IfcDistributionPort: "Distribution Port",
  IfcFlowTerminal: "Terminal",
  IfcFlowSegment: "Duct Segment",
  IfcFlowFitting: "Duct Fitting",
  IfcSpace: "Space",
  IfcBuildingStorey: "Building Level",
  IfcValve: "Valve",
  IfcFan: "Fan",
};

const FRIENDLY_RELATIONS = {
  CONNECTED_TO: "Connected To",
  FEEDS: "Feeds",
  CONTAINS: "Contains",
  ASSIGNED_TO_SYSTEM: "Assigned To System",
};

const friendlyType = (t) => {
  if (!t) return t;
  return FRIENDLY_TYPES[t] ?? t.replace(/([a-z0-9])([A-Z])/g, "$1 $2");
};

const friendlyRelation = (r) => FRIENDLY_RELATIONS[r] ?? r;
const sectionIds = ["hero", "graph", "assist", "work"];
const primaryButtonClass =
  "bg-[var(--primary)] text-[var(--primary-foreground)] hover:opacity-90 focus-visible:ring-[var(--ring)] focus-visible:ring-2 ring-offset-1";

// Minimal message bubble
function ChatBubble({ role, text }) {
  const isUser = role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-snug shadow-sm ${isUser ? "bg-[var(--chart-1)] text-[var(--foreground)]" : "bg-[var(--card)] text-[var(--card-foreground)]"}`}
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
  const [selectedIfc, setSelectedIfc] = useState(null);

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
  const graphContainerRef = useRef(null);
  const [graphSize, setGraphSize] = useState({ width: 0, height: 0 });
  const [activeSection, setActiveSection] = useState("hero");
  const [activePanel, setActivePanel] = useState("graph");

  // Work orders
  const [orders, setOrders] = useLocalOrders();
  const [woDraft, setWoDraft] = useState({ title: "", priority: "Medium", assetId: "" });
  const railActions = useMemo(
    () => [
      { icon: Factory, label: "Overview", target: "hero" },
      { icon: Network, label: "Graph", target: "graph" },
      { icon: MessageSquare, label: "Assist", target: "assist" },
      { icon: Wrench, label: "Work", target: "work" },
    ],
    []
  );

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
        setAsset({ ...data, friendlyType: friendlyType(data.type) });
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

  const runQuery = useCallback(
    async (incomingText) => {
      const raw = incomingText ?? q;
      const text = raw.trim();
      if (!text) return;
      if (incomingText !== undefined) {
        setQ(incomingText);
      }

      addMsg({ role: "user", text });
      setBusy(true);

      try {
        const res = await fetch(api("/chat"), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            message: text,
            history: messages.map((m) => ({ role: m.role, content: m.text })),
          }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || JSON.stringify(data));

        const tool = data.tool || {};
        if (tool.action === "count") {
          setHits([]);
          setGraphData({ nodes: [], links: [] });
          setAsset(null);
          addMsg({ role: "assistant", text: data.reply });
        } else if (tool.action === "search") {
          const hitsPayload = (tool.hits || []).map((h) => ({
            ...h,
            friendlyType: friendlyType(h.type),
          }));
          setHits(hitsPayload);
          setActivePanel("graph");
          setActiveSection("graph");

          const nodes = [];
          const links = [];
          const seen = new Set();
          (tool.subgraphs || []).forEach((sg) => {
            (sg.nodes || []).forEach((n) => {
              if (seen.has(n.id)) return;
              seen.add(n.id);
              nodes.push({
                id: n.id,
                name: n.name || "(unnamed)",
                type: n.type || "",
                friendlyType: friendlyType(n.type || ""),
                source: n.source || "",
              });
            });
            (sg.edges || []).forEach((e) => {
              links.push({
                source: e.src,
                target: e.dst,
                type: e.type,
                friendlyType: friendlyRelation(e.type),
              });
            });
          });

          const degree = {};
          links.forEach((edge) => {
            if (edge.source) degree[edge.source] = (degree[edge.source] || 0) + 1;
            if (edge.target) degree[edge.target] = (degree[edge.target] || 0) + 1;
          });
          const enrichedNodes = nodes.map((n) => ({ ...n, degree: degree[n.id] || 0 }));

          setGraphData({ nodes: enrichedNodes, links });

          const primary = hitsPayload[0]?.id || enrichedNodes[0]?.id;
          if (primary) await openAsset(primary);

          addMsg({ role: "assistant", text: data.reply });
        } else {
          addMsg({ role: "assistant", text: data.reply || "I’m here if you need anything else." });
        }
      } catch (e) {
        console.error(e);
        addMsg({ role: "assistant", text: `Error: ${String(e.message || e)}` });
      } finally {
        setBusy(false);
      }
    },
    [addMsg, messages, openAsset, q]
  );

  const handleSelectedNeighbors = useCallback(() => {
    if (!selectedIfc) return;
    const label = selectedIfc.name || selectedIfc.globalId;
    if (!label) return;
    const prompt = `Show connections around ${label}`;
    runQuery(prompt);
  }, [selectedIfc, runQuery]);

  const clearSelectedIfc = useCallback(() => {
    setSelectedIfc(null);
    try {
      viewerRef.current?.IFC?.selector?.unpickIfcItems?.();
    } catch (err) {
      console.warn("Failed to clear IFC selection", err);
    }
  }, []);

  const focusSelectedIfc = useCallback(() => {
    if (!selectedIfc || !viewerRef.current) return;
    try {
      viewerRef.current.IFC.selector.highlightIfcItemByID?.(
        selectedIfc.modelID,
        selectedIfc.expressID,
        true
      );
      viewerRef.current.IFC.selector.pickIfcItem(true);
    } catch (err) {
      console.warn("Unable to focus IFC element", err);
    }
  }, [selectedIfc]);

  const decisionActions = useMemo(
    () => [
      { label: "Show HVAC", prompt: "Show HVAC assets and their status" },
      { label: "Open Issues", prompt: "List assets with open work orders" },
      { label: "Energy Hotspots", prompt: "Highlight zones with high energy usage" },
    ],
    []
  );

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

        const onClick = async () => {
          const result = await viewer.IFC.selector.pickIfcItem(false, true);
          if (!result) {
            setSelectedIfc(null);
            return;
          }
          try {
            const { modelID, id: expressID } = result;
            const props = await viewer.IFC.getProperties(modelID, expressID, true, true);
            const globalId = props?.GlobalId?.value;
            const name = props?.Name?.value || props?.Tag?.value || "Unnamed";
            const typeName = props?.type || props?.expressType || props?.EntityLabel;
            setSelectedIfc({ modelID, expressID, globalId, name, typeName });
            if (globalId) {
              await openAsset(globalId);
            }
          } catch (err) {
            console.warn("IFC selection failed", err);
          }
        };
        const controlsEl = viewer.context.ifcCamera?.controls?.domElement;
        controlsEl?.addEventListener("click", onClick);

        viewer.IFC.selector.prePickIfcItem = true;
        viewer.IFC.selector.highlightIfcItem();

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
      try {
        viewerRef.current?.context?.ifcCamera?.controls?.domElement?.removeEventListener("click", onClick);
      } catch (err) {
        console.warn("Failed to detach IFC click handler", err);
      }
      viewerRef.current?.dispose?.();
      viewerRef.current = null;
    };
  }, [addMsg]);

  useEffect(() => {
    const el = graphContainerRef.current;
    if (!el || typeof ResizeObserver === "undefined") return;

    const updateSize = () => {
      setGraphSize({ width: el.clientWidth, height: el.clientHeight });
    };
    updateSize();

    const observer = new ResizeObserver(() => updateSize());
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (typeof IntersectionObserver === "undefined") return;
    const elements = sectionIds
      .map((id) => document.getElementById(`rig-section-${id}`))
      .filter(Boolean);
    if (!elements.length) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio);
        if (visible.length) {
          const id = visible[0].target.id.replace("rig-section-", "");
          setActiveSection(id);
        }
      },
      {
        threshold: [0.35, 0.6],
        rootMargin: "-120px 0px -40%",
      }
    );

    elements.forEach((el) => observer.observe(el));
    return () => {
      elements.forEach((el) => observer.unobserve(el));
      observer.disconnect();
    };
  }, [railActions]);

  const drawNode = useCallback((node, ctx, scale) => {
    const radius = 5 + Math.log((node.degree || 1) + 1) * 2;
    ctx.beginPath();
    ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI, false);
    ctx.fillStyle = node.type?.startsWith("IfcFlow")
      ? "#38bdf8"
      : node.type?.startsWith("IfcSpace")
      ? "#34d399"
      : "#e2e8f0";
    ctx.fill();
    ctx.font = `${Math.max(11 / scale, 8)}px Inter, system-ui`;
    ctx.fillStyle = "#0f172a";
    const label = node.friendlyType || node.name?.slice(0, 36) || node.id;
    ctx.fillText(label, node.x + radius + 4, node.y + 4);
  }, []);

  const recentMessages = messages.slice(-6);

  return (
    <div className="flex min-h-screen flex-col bg-[var(--background)] text-[var(--foreground)]">
      <header className="flex items-center gap-3 border-b border-[var(--sidebar-border)] bg-[var(--sidebar)] px-6 py-4 shadow-sm">
        <Factory className="h-6 w-6 text-[var(--sidebar-primary)]" />
        <div>
          <h1 className="text-xl font-semibold">RiG <em>it</em></h1>
          <p className="text-xs text-[var(--sidebar-foreground)]">Monitor, explore, and act across your facility in one console.</p>
        </div>
        <Badge className="ml-2 bg-[var(--sidebar-accent)] text-[var(--sidebar-foreground)]">GraphRAG + IFC</Badge>
        <div className="ml-auto flex items-center gap-2 text-xs text-[#F5EBFF]">
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

      <div className="flex flex-1 overflow-hidden">
        <aside className="hidden w-24 flex-col justify-between border-r border-[var(--sidebar-border)] bg-[var(--sidebar)] px-2 py-6 xl:flex text-[var(--sidebar-foreground)]">
          <div className="space-y-6">
            {railActions.map(({ icon: Icon, label, target }) => (
              <button
                key={label}
                className={cn(
                  "flex w-full flex-col items-center justify-center gap-1 rounded-2xl border px-2 py-3 text-xs font-medium leading-tight shadow-sm transition text-center",
                  activeSection === target
                    ? "border-[var(--sidebar-primary)] bg-[var(--sidebar-primary)] text-[var(--sidebar-primary-foreground)] shadow-lg"
                    : "border-[var(--sidebar-border)] bg-[var(--sidebar)] text-[var(--sidebar-foreground)] hover:bg-[color-mix(in, var(--sidebar-primary) 8%, var(--sidebar))]"
                )}
                type="button"
                onClick={() => {
                  const el = target ? document.getElementById(`rig-section-${target}`) : null;
                  if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
                  setActiveSection(target);
                  setActivePanel(target === "hero" ? "graph" : target);
                }}
              >
                <Icon className="h-5 w-5" />
                <span className="mt-1 text-[11px]">{label}</span>
              </button>
            ))}
          </div>
          <div className="rounded-2xl bg-slate-900 px-3 py-4 text-center text-xs text-white">
            <div className="text-lg font-semibold">{orders.length}</div>
            <div className="text-[10px] uppercase tracking-wide">Open work orders</div>
          </div>
        </aside>

        <main className="flex-1 overflow-y-auto">
          <div className="mx-auto flex h-full max-w-[1500px] flex-col gap-6 px-6 pb-24 pt-6">
            <div className="grid flex-1 gap-6 xl:grid-cols-[minmax(0,1.6fr)_minmax(320px,1.1fr)]">
              <section
                id="rig-section-hero"
                className={cn(
                  "relative flex min-h-[calc(100vh-200px)] flex-col overflow-hidden rounded-3xl border bg-[var(--card)] transition-all duration-300",
                  activeSection === "hero"
                    ? "border-[var(--primary)] shadow-xl ring-2 ring-[var(--primary)]"
                    : "border-[var(--border)] shadow-lg opacity-95"
                )}
              >
                <div className="relative flex-1 overflow-hidden bg-gradient-to-br from-[var(--card)] to-[var(--popover)]">
                  <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(148,163,184,0.18),_transparent_60%)]" />
                  <div className="pointer-events-none absolute inset-y-12 inset-x-16 rounded-[38px] border border-white/60 shadow-[0_30px_120px_-40px_rgba(15,23,42,0.35)]" />
                  {/* IFC viewer lives behind overlays; lower z-index to avoid overlapping footer/chat */}
                  <div ref={ifcContainerRef} className="absolute inset-0 z-0 h-full w-full" />
                  {!defaultIfcLoadedRef.current && (
                    <div className="pointer-events-none absolute inset-0 flex items-center justify-center z-20">
                        <div className="rounded-3xl border border-[var(--border)] bg-[var(--popover)]/95 px-6 py-5 text-center shadow-lg">
                          <div className="text-xs uppercase tracking-wide text-[var(--muted-foreground)]">IFC viewer</div>
                          <div className="mt-2 text-lg font-semibold text-[var(--foreground)]">Loading facility model…</div>
                          <div className="mt-2 text-xs text-[var(--muted-foreground)]">Drop an IFC file or wait for the default sample.</div>
                        </div>
                      </div>
                  )}
                </div>
                <div className="pointer-events-none absolute inset-x-0 bottom-0 h-24 bg-gradient-to-t from-[var(--card)] to-transparent z-10" />
                <div className="absolute left-6 top-6 space-y-2 rounded-2xl bg-[var(--popover)] px-4 py-3 text-sm shadow-md z-30">
                  <div className="text-xs uppercase tracking-wide text-[var(--muted-foreground)]">Facility</div>
                  <div className="text-base font-semibold">Building Twin</div>
                  <div className="flex gap-3 text-xs text-[var(--muted-foreground)]">
                    <span>{graphData.nodes.length} nodes</span>
                    <span>{graphData.links.length} links</span>
                  </div>
                </div>
                  <div className="absolute right-6 top-6 z-40 flex flex-col items-end gap-3">
                    <div className="flex flex-wrap justify-end gap-2">
                    {decisionActions.map((action) => (
                      <button
                        key={action.label}
                        type="button"
                        className="rounded-full border border-[var(--border)] bg-[var(--popover)] px-4 py-2 text-xs font-semibold text-[var(--foreground)] shadow-sm transition hover:border-[var(--primary)]"
                        onClick={() => runQuery(action.prompt)}
                      >
                        {action.label}
                      </button>
                    ))}
                  </div>
                  {(selectedIfc || asset) && (
                    <div className="absolute bottom-6 right-6 w-80 rounded-2xl border border-[var(--border)] bg-[var(--card)] p-4 shadow-xl z-50">
                      <div className="flex items-center justify-between text-xs text-[var(--muted-foreground)]">
                        <span>Selected element</span>
                        <button
                          type="button"
                          className="text-[var(--muted-foreground)] transition hover:text-[var(--foreground)]"
                          onClick={clearSelectedIfc}
                        >
                          Clear
                        </button>
                      </div>
                      <div className="mt-2 text-lg font-semibold text-[var(--foreground)]">
                        {selectedIfc?.name || asset?.name || "(unnamed)"}
                      </div>
                      <div className="text-xs text-[var(--muted-foreground)]">
                        {friendlyType(selectedIfc?.typeName || asset?.type)}
                      </div>
                      <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
                        <Button
                          size="sm"
                          variant="ghost"
                          className={primaryButtonClass}
                          onClick={() => {
                            const id = selectedIfc?.globalId || asset?.id;
                            if (id) openAsset(id);
                          }}
                        >
                          Open asset
                        </Button>
                        <Button size="sm" variant="outline" onClick={handleSelectedNeighbors}>
                          Graph context
                        </Button>
                        <Button size="sm" variant="outline" onClick={focusSelectedIfc}>
                          Highlight
                        </Button>
                        <Button size="sm" variant="ghost" onClick={clearSelectedIfc}>
                          Dismiss
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              </section>

              <aside className="relative" id="rig-section-panel">
                <div className="sticky top-6 space-y-4">
                    {activePanel === "graph" && (
                    <Card className="min-h-[calc(100vh-240px)] overflow-hidden rounded-3xl border border-[var(--border)] bg-[var(--card)] shadow-lg transition-all">
                      <CardHeader className="flex items-center justify-between py-3">
                        <CardTitle className="flex items-center gap-2 text-base">
                          <Network className="h-4 w-4" /> Model Graph
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="flex-1 overflow-hidden rounded-b-[22px] bg-[var(--card)] p-0">
                        <div ref={graphContainerRef} className="h-full min-h-[420px] w-full" style={{minHeight: 420}}>
                          {graphSize.width > 0 && graphSize.height > 0 && (
                            <ForceGraph2D
                              graphData={graphData}
                              nodeId="id"
                              nodeCanvasObject={drawNode}
                              linkDirectionalArrowLength={4}
                              linkColor={() => "#94a3b8"}
                              onNodeClick={(n) => openAsset(n.id)}
                              width={graphSize.width}
                              height={graphSize.height}
                            />
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  )}

                  {activePanel === "assist" && (
                    <Card className="max-h-[calc(100vh-200px)] overflow-hidden rounded-3xl border border-[var(--border)] bg-[var(--card)] shadow-lg">
                      <CardHeader className="py-3">
                        <CardTitle className="text-base">Asset Details</CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-3 overflow-auto pr-2">
                        {!asset && <div className="text-sm text-[var(--muted-foreground)]">Select a node, hit, or work order to view details.</div>}
                        {asset && (
                          <div className="space-y-3">
                            <div className="text-xs text-slate-400">{asset.id}</div>
                            <div className="text-lg font-semibold leading-tight">{asset.name || "(unnamed asset)"}</div>
                            <div className="flex flex-wrap items-center gap-2 text-xs">
                              <Badge variant="outline">{asset.friendlyType || friendlyType(asset.type)}</Badge>
                              {asset.source && <Badge variant="secondary">{asset.source}</Badge>}
                            </div>
                            <div className="grid grid-cols-3 gap-2 text-sm">
                              {asset.x !== undefined && (
                                <div className="rounded-lg bg-[var(--popover)] px-2 py-1">
                                  <div className="text-xs uppercase text-[var(--muted-foreground)]">coord.x</div>
                                  <div className="font-mono text-sm">{Math.round(asset.x)}</div>
                                </div>
                              )}
                              {asset.y !== undefined && (
                                <div className="rounded-lg bg-[var(--popover)] px-2 py-1">
                                  <div className="text-xs uppercase text-[var(--muted-foreground)]">coord.y</div>
                                  <div className="font-mono text-sm">{Math.round(asset.y)}</div>
                                </div>
                              )}
                              {asset.z !== undefined && (
                                <div className="rounded-lg bg-[var(--popover)] px-2 py-1">
                                  <div className="text-xs uppercase text-[var(--muted-foreground)]">coord.z</div>
                                  <div className="font-mono text-sm">{Math.round(asset.z)}</div>
                                </div>
                              )}
                            </div>
                            {asset.psets && (
                              <div>
                                <div className="text-sm font-medium">Property Sets</div>
                                <pre className="max-h-48 overflow-auto rounded-xl bg-[var(--popover)] p-3 text-xs">
                                  {JSON.stringify(asset.psets, null, 2)}
                                </pre>
                              </div>
                            )}
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  )}

                    {activePanel === "graph" && (
                    <Card className="max-h-[360px] overflow-hidden rounded-3xl border border-[var(--border)] bg-[var(--card)] shadow-lg">
                      <CardHeader className="py-3">
                        <CardTitle className="text-base">Related Hits</CardTitle>
                        <p className="text-xs text-slate-500">
                          {hits.length
                            ? `Showing ${hits.length} items linked to your last question.`
                            : "Run a search to populate this panel."}
                        </p>
                      </CardHeader>
                      <CardContent className="space-y-3 overflow-auto pr-2">
                        {!hits.length && (
                          <div className="rounded-2xl border border-dashed border-[var(--border)] bg-[var(--popover)] px-4 py-6 text-center text-sm text-[var(--muted-foreground)]">
                            Results will appear here once you ask the model about the facility.
                          </div>
                        )}
                        {hits.map((h, i) => (
                          <div
                            key={h.id || i}
                            className="rounded-2xl border border-[var(--border)] bg-[var(--popover)] px-3 py-3 shadow-sm transition hover:border-[var(--primary)]"
                          >
                            <div className="flex items-center gap-2">
                              <div className="flex-1">
                                <div className="font-semibold leading-tight">{h.name || "(unnamed)"}</div>
                                <div className="text-xs text-[var(--muted-foreground)]">{h.id}</div>
                              </div>
                              {typeof h.score === "number" && (
                                <span className="rounded-full bg-[var(--popover)] px-2 py-1 text-[11px] font-medium text-[var(--muted-foreground)]">
                                  {(h.score * 100).toFixed(1)}%
                                </span>
                              )}
                            </div>
                            <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px] text-[var(--muted-foreground)]">
                              <Badge variant="outline">{h.friendlyType || friendlyType(h.type)}</Badge>
                              {h.storeys?.length ? (
                                <span className="rounded-full bg-[var(--popover)] px-2 py-1">{h.storeys.join(", ")}</span>
                              ) : null}
                              {h.rooms?.length ? (
                                <span className="rounded-full bg-[var(--popover)] px-2 py-1">{h.rooms.join(", ")}</span>
                              ) : null}
                            </div>
                            <div className="mt-3 flex gap-2">
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => {
                                  openAsset(h.id);
                                  setActivePanel("assist");
                                }}
                              >
                                View asset
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => {
                                  runQuery(`Show neighboring assets for ${h.name || h.id}`);
                                  setActiveSection("graph");
                                }}
                              >
                                Expand graph
                              </Button>
                            </div>
                          </div>
                        ))}
                      </CardContent>
                    </Card>
                  )}

                  {activePanel === "work" && (
                    <Card className="overflow-hidden rounded-3xl border border-[var(--border)] bg-[var(--card)] shadow-lg">
                      <CardHeader className="py-3">
                        <CardTitle className="flex items-center gap-2 text-base">
                          <Wrench className="h-4 w-4" /> Work Orders
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="flex h-full flex-col gap-3">
                        <div className="grid grid-cols-6 items-end gap-2 text-xs">
                          <div className="col-span-3 space-y-1">
                            <Label className="text-xs font-semibold uppercase tracking-wide text-[var(--muted-foreground)]">Title</Label>
                            <Input
                              className="bg-[var(--card)]"
                              placeholder="title"
                              value={woDraft.title}
                              onChange={(e) => setWoDraft({ ...woDraft, title: e.target.value })}
                            />
                          </div>
                          <div className="col-span-1 space-y-1">
                            <Label className="text-xs font-semibold uppercase tracking-wide text-[var(--muted-foreground)]">Priority</Label>
                            <Select value={woDraft.priority} onValueChange={(v) => setWoDraft({ ...woDraft, priority: v })}>
                              <SelectTrigger className="bg-[var(--card)]">
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
                            <Label className="text-xs font-semibold uppercase tracking-wide text-[var(--muted-foreground)]">Asset ID</Label>
                            <Input
                              className="bg-[var(--card)]"
                              placeholder="asset id"
                              value={woDraft.assetId}
                              onChange={(e) => setWoDraft({ ...woDraft, assetId: e.target.value })}
                            />
                          </div>
                        </div>
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            variant="ghost"
                            className={primaryButtonClass}
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
                        <div className="flex-1 space-y-2 overflow-auto pr-1">
                          {!orders.length && <div className="text-sm text-[var(--muted-foreground)]">No work orders.</div>}
                          {orders.map((o) => (
                            <div key={o.id} className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-3 text-sm shadow-sm">
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
                                <span className="text-[var(--muted-foreground)]">{o.status}</span>
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
                  )}
                </div>
              </aside>

            </div>
          </div>
        </main>
      </div>

  <footer className="sticky bottom-0 border-t border-[var(--border)] bg-[var(--card)] px-6 py-5 z-50">
        <div className="mx-auto max-w-[1400px] space-y-3">
          <div className="flex gap-2 overflow-x-auto pb-1">
            {recentMessages.map((m, i) => (
              <div
                key={`${m.role}-${i}`}
                className={`min-w-[200px] rounded-2xl px-4 py-3 text-xs shadow-sm ${
                  m.role === "user" ? "bg-[var(--primary)] text-[var(--primary-foreground)]" : "bg-[var(--popover)] text-[var(--popover-foreground)]"
                }`}
              >
                <div className="mb-1 font-medium uppercase tracking-wide text-[10px] opacity-70">
                  {m.role === "user" ? "You" : "Assistant"}
                </div>
                {m.text}
              </div>
            ))}
          </div>

          <div className="flex flex-col gap-3 md:flex-row md:items-end">
            <div className="flex-1 space-y-1">
              <Label htmlFor="rig-query" className="text-xs font-semibold uppercase tracking-wide text-[var(--muted-foreground)]">
                Ask the model
              </Label>
              <Input
                id="rig-query"
                className="bg-[var(--card)]"
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="How can we help with this facility?"
              />
            </div>
            <div className="flex flex-wrap items-end gap-2">
              <div className="space-y-1">
                <Label htmlFor="rig-k" className="text-[10px] font-semibold uppercase tracking-wide text-[var(--muted-foreground)]">
                  Top-k
                </Label>
                <Input
                  id="rig-k"
                  type="number"
                  inputMode="numeric"
                  min={1}
                  max={50}
                  className="w-20 bg-[var(--card)] text-center"
                  value={k}
                  onChange={(e) => setK(Math.max(1, Number(e.target.value) || 10))}
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="rig-hops" className="text-[10px] font-semibold uppercase tracking-wide text-[var(--muted-foreground)]">
                  Hops
                </Label>
                <Input
                  id="rig-hops"
                  type="number"
                  inputMode="numeric"
                  min={1}
                  max={5}
                  className="w-20 bg-[var(--card)] text-center"
                  value={hops}
                  onChange={(e) => setHops(Math.max(1, Number(e.target.value) || 2))}
                />
              </div>
              <Button
                variant="ghost"
                className={cn("h-10 px-6", primaryButtonClass)}
                onClick={runQuery}
                disabled={busy}
              >
                <Send className="mr-1 h-4 w-4" />
                {busy ? "Working…" : "Send"}
              </Button>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
