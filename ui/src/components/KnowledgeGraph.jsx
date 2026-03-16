import React, { useEffect, useState } from 'react';
import { Search, ChevronRight, ArrowLeft, Loader2, Network } from 'lucide-react';
import { API_BASE } from '@/lib/env';

const NS_COLORS = {
  s223: '#a855f7',
  brick: '#22c55e',
  ifc: '#3b82f6',
  ifcid: '#60a5fa',
  co: '#f59e0b',
  bldg: '#34d399',
  qudt: '#06b6d4',
  qk: '#06b6d4',
  rig: '#ec4899',
  skos: '#facc15',
  rdfs: '#94a3b8',
  rdf: '#94a3b8',
  other: '#64748b',
};

function getNodeColor(node) {
  if (node.type === 'class') return '#f59e0b';
  if (node.type === 'literal') return '#94a3b8';
  return NS_COLORS[node.ns] || NS_COLORS.other;
}

const KnowledgeGraph = ({ onNodeClick }) => {
  const [topNodes, setTopNodes] = useState([]);
  const [filteredNodes, setFilteredNodes] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [selected, setSelected] = useState(null);
  const [focusedGraph, setFocusedGraph] = useState(null);
  const [loadingList, setLoadingList] = useState(true);
  const [loadingGraph, setLoadingGraph] = useState(false);
  const [history, setHistory] = useState([]);

  useEffect(() => {
    loadTopNodes();
  }, []);

  useEffect(() => {
    if (!searchTerm.trim()) {
      setFilteredNodes(topNodes);
      return;
    }
    const q = searchTerm.toLowerCase();
    setFilteredNodes(
      topNodes.filter(n =>
        (n.label || '').toLowerCase().includes(q) ||
        (n.id || '').toLowerCase().includes(q) ||
        (n.types || []).some(t => t.toLowerCase().includes(q))
      )
    );
  }, [searchTerm, topNodes]);

  const loadTopNodes = async () => {
    setLoadingList(true);
    try {
      const res = await fetch(`${API_BASE}/graphdb/hierarchy`);
      const data = await res.json();
  
      const hierarchyNodes = (data.nodes || []).map(n => ({
        uri: n.id,
        id: n.id,
        label: n.label || n.name || n.id,
        types: n.rdfType ? [n.rdfType] : [],
        ns: n.ns || 'other',
      }));
  
      setTopNodes(hierarchyNodes);
      setFilteredNodes(hierarchyNodes);
    } catch (err) {
      console.error('Failed to load hierarchy:', err);
      setTopNodes([]);
      setFilteredNodes([]);
    } finally {
      setLoadingList(false);
    }
  };

  const loadFocusedGraph = async (uri, pushHistory = true) => {
    setLoadingGraph(true);
    try {
      const res = await fetch(`${API_BASE}/graphdb/focus?uri=${encodeURIComponent(uri)}&limit=40`);
      const data = await res.json();

      if (pushHistory && selected?.uri) {
        setHistory(prev => [...prev, selected]);
      }

      const centerNode = data.nodes?.find(n => n.id === uri) || { id: uri, label: uri, name: uri };
      setSelected({ uri, label: centerNode.label || centerNode.name || uri });
      setFocusedGraph(data);

      if (onNodeClick) {
        onNodeClick({
          id: uri,
          uri,
          label: centerNode.label || centerNode.name || uri,
        });
      }
    } catch (err) {
      console.error('Failed to load focused graph:', err);
    } finally {
      setLoadingGraph(false);
    }
  };

  const goBack = () => {
    if (history.length === 0) {
      setSelected(null);
      setFocusedGraph(null);
      return;
    }
    const prev = history[history.length - 1];
    setHistory(h => h.slice(0, -1));
    loadFocusedGraph(prev.uri, false);
  };

  if (!selected || !focusedGraph) {
    return (
      <div className="h-full w-full flex flex-col bg-nexus-800 rounded-lg border border-nexus-600 overflow-hidden">
        <div className="flex-shrink-0 px-4 pt-4 pb-2">
          <h3 className="text-xs font-mono text-nexus-accent uppercase tracking-widest mb-2">
            Focused Graph Explorer
          </h3>
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              placeholder="Search entities..."
              className="w-full bg-nexus-900/50 text-slate-200 placeholder:text-slate-500 border border-nexus-700 rounded-lg py-2 pl-9 pr-4 focus:outline-none focus:border-nexus-accent/50 text-sm"
            />
          </div>
          <p className="text-[10px] text-slate-600 mt-1.5 font-mono">
            CASE hierarchy entry points from IFC-LD, Brick, 223P, and overlay links
          </p>
        </div>

        <div className="flex-1 overflow-y-auto px-4 pb-4 custom-scrollbar">
          {loadingList ? (
            <div className="flex items-center justify-center h-40">
              <Loader2 size={20} className="animate-spin text-nexus-accent" />
            </div>
          ) : filteredNodes.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-40 text-slate-500">
              <Network size={32} className="mb-2 opacity-20" />
              <p className="text-sm">No entities found</p>
            </div>
          ) : (
            <div className="space-y-2">
              {filteredNodes.map((n) => (
                <button
                  key={n.uri}
                  onClick={() => loadFocusedGraph(n.uri)}
                  className="w-full text-left flex items-center gap-2 px-3 py-2 bg-nexus-900/30 border border-nexus-700/50 rounded-lg hover:border-nexus-accent/40 hover:bg-nexus-900/60 transition-all group"
                >
                  <span
                    className="w-2 h-2 rounded-full flex-shrink-0"
                    style={{ backgroundColor: NS_COLORS[n.ns] || NS_COLORS.other }}
                  />
                  <div className="min-w-0 flex-1">
                    <div className="text-sm text-slate-300 group-hover:text-white truncate">
                      {n.label}
                    </div>
                    <div className="text-[10px] text-slate-500 font-mono truncate">
                      {(n.types || []).join(', ')}
                    </div>
                  </div>
                  <ChevronRight size={14} className="text-slate-600 group-hover:text-nexus-accent flex-shrink-0 transition-colors" />
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  }

  const center = focusedGraph.nodes.find(n => n.id === focusedGraph.center);
  const edges = focusedGraph.edges || [];
  const nodesById = Object.fromEntries((focusedGraph.nodes || []).map(n => [n.id, n]));

  return (
    <div className="h-full w-full flex flex-col bg-nexus-800 rounded-lg border border-nexus-600 overflow-hidden">
      <div className="flex-shrink-0 px-4 pt-3 pb-2 border-b border-nexus-700/50">
        <div className="flex items-center gap-2">
          <button onClick={goBack} className="p-1 rounded hover:bg-nexus-700 text-slate-400 hover:text-white transition-colors">
            <ArrowLeft size={16} />
          </button>
          <div className="text-sm text-white font-medium truncate">
            {center?.label || center?.name || selected.label}
          </div>
        </div>
        <p className="text-[10px] text-slate-500 font-mono mt-1 truncate">
          {selected.uri}
        </p>
      </div>

      <div className="flex-1 overflow-y-auto p-4 custom-scrollbar">
        {loadingGraph ? (
          <div className="flex items-center justify-center h-full">
            <Loader2 size={20} className="animate-spin text-nexus-accent" />
          </div>
        ) : (
          <div className="grid grid-cols-[280px_1fr] gap-6 min-h-full">
            {/* Center card */}
            <div className="bg-nexus-900/50 border border-nexus-700 rounded-xl p-4 h-fit sticky top-0">
              <div className="flex items-center gap-3 mb-3">
                <span
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: getNodeColor(center || {}) }}
                />
                <div className="text-white font-medium">
                  {center?.label || center?.name || 'Selected Node'}
                </div>
              </div>
              <div className="text-[11px] text-slate-400 font-mono">
                {center?.id}
              </div>
              <div className="mt-3 text-[11px] text-slate-500">
                Type: {center?.type || 'resource'}
              </div>
            </div>

            {/* Relations */}
            <div className="space-y-3">
              {edges.length === 0 ? (
                <div className="text-slate-500 text-sm">No related triples found.</div>
              ) : (
                edges.map((e, i) => {
                  const target = nodesById[e.target];
                  const clickable = target && !String(target.id).startsWith('_:') && target.type !== 'literal';

                  return (
                    <div
                      key={`${e.source}-${e.target}-${e.predicate}-${i}`}
                      className="flex items-center gap-3 bg-nexus-900/30 border border-nexus-700/40 rounded-xl p-3"
                    >
                      <div className="min-w-[140px] text-[11px] font-mono text-nexus-accent">
                        {e.predicate}
                      </div>

                      <div className="text-slate-500">→</div>

                      {target ? (
                        clickable ? (
                          <button
                            onClick={() => loadFocusedGraph(target.id)}
                            className="flex items-center gap-2 text-left hover:bg-nexus-800/60 rounded-lg px-2 py-1 transition-colors"
                          >
                            <span
                              className="w-2.5 h-2.5 rounded-full"
                              style={{ backgroundColor: getNodeColor(target) }}
                            />
                            <div>
                              <div className="text-sm text-white">
                                {target.label || target.name}
                              </div>
                              <div className="text-[10px] text-slate-500 font-mono truncate max-w-[420px]">
                                {target.id}
                              </div>
                            </div>
                          </button>
                        ) : (
                          <div className="flex items-center gap-2 px-2 py-1">
                            <span
                              className="w-2.5 h-2.5 rounded-full"
                              style={{ backgroundColor: getNodeColor(target) }}
                            />
                            <div>
                              <div className="text-sm text-slate-200">
                                {target.label || target.name}
                              </div>
                              <div className="text-[10px] text-slate-500 font-mono truncate max-w-[420px]">
                                {target.id}
                              </div>
                            </div>
                          </div>
                        )
                      ) : (
                        <div className="text-slate-400 text-sm">Unknown target</div>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default KnowledgeGraph;