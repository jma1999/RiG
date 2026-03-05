import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Database, ChevronRight, ExternalLink, Search, Loader2, ArrowLeft } from 'lucide-react';
import { API_BASE } from '@/lib/env';

const NS_COLORS = {
  s223:  '#a855f7',
  brick: '#22c55e',
  ifc:   '#3b82f6',
  ifcid: '#60a5fa',
  co:    '#f59e0b',
  bldg:  '#34d399',
  qudt:  '#06b6d4',
  qk:    '#06b6d4',
  rig:   '#ec4899',
  skos:  '#facc15',
  rdfs:  '#94a3b8',
  rdf:   '#94a3b8',
  other: '#64748b',
};

function nsColor(ns) {
  return NS_COLORS[ns] || NS_COLORS.other;
}

// Radial layout helper: places child nodes in a half-circle around center
function radialPositions(cx, cy, count, radius) {
  if (count === 0) return [];
  const positions = [];
  const startAngle = -Math.PI / 2;
  const sweep = Math.PI * 1.6;
  for (let i = 0; i < count; i++) {
    const angle = startAngle + (count === 1 ? 0 : (sweep * i) / (count - 1)) - sweep / 2 + Math.PI / 2;
    positions.push({
      x: cx + radius * Math.cos(angle),
      y: cy + radius * Math.sin(angle),
    });
  }
  return positions;
}


const NodeGraph = ({ node, triples, onExpandUri, containerWidth, containerHeight }) => {
  const cx = containerWidth / 2;
  const cy = containerHeight / 2;
  const radius = Math.min(containerWidth, containerHeight) * 0.36;
  const positions = radialPositions(cx, cy, triples.length, radius);

  return (
    <svg width={containerWidth} height={containerHeight} className="select-none">
      {/* Edges */}
      {triples.map((t, i) => (
        <line
          key={`edge-${i}`}
          x1={cx} y1={cy}
          x2={positions[i].x} y2={positions[i].y}
          stroke={t.isUri ? '#4fd1c5' : '#334155'}
          strokeWidth={1.2}
          strokeOpacity={0.5}
        />
      ))}

      {/* Central node */}
      <circle cx={cx} cy={cy} r={22} fill="#f59e0b" fillOpacity={0.15} stroke="#f59e0b" strokeWidth={2} />
      <text x={cx} y={cy + 1} textAnchor="middle" dominantBaseline="middle"
        className="text-[11px] font-semibold fill-amber-300" style={{ fontFamily: 'Inter, system-ui, sans-serif' }}>
        {node.label?.length > 18 ? node.label.slice(0, 16) + '…' : node.label}
      </text>

      {/* Property nodes */}
      {triples.map((t, i) => {
        const { x, y } = positions[i];
        const isUri = t.isUri;
        const nodeR = 6;
        const labelText = `${t.predicate}: ${t.value}`;
        const truncatedLabel = labelText.length > 55 ? labelText.slice(0, 52) + '…' : labelText;

        // Determine label anchor based on position relative to center
        const isRight = x >= cx;
        const textX = isRight ? x + nodeR + 6 : x - nodeR - 6;
        const anchor = isRight ? 'start' : 'end';

        return (
          <g key={`node-${i}`}
            className={isUri ? 'cursor-pointer' : ''}
            onClick={() => isUri && onExpandUri(t.rawValue)}
          >
            <circle
              cx={x} cy={y} r={nodeR}
              fill={isUri ? (nsColor(t.ns) + '40') : 'transparent'}
              stroke={isUri ? nsColor(t.ns) : '#475569'}
              strokeWidth={1.5}
            />
            {isUri && (
              <circle cx={x} cy={y} r={3} fill={nsColor(t.ns)} />
            )}
            <text
              x={textX} y={y + 1}
              textAnchor={anchor}
              dominantBaseline="middle"
              className={`text-[10px] ${isUri ? 'fill-teal-300 hover:fill-teal-100' : 'fill-slate-400'}`}
              style={{ fontFamily: '"SF Mono", Menlo, monospace' }}
            >
              {truncatedLabel}
            </text>
          </g>
        );
      })}
    </svg>
  );
};


const KnowledgeGraph = ({ data, onNodeClick }) => {
  const [topNodes, setTopNodes] = useState([]);
  const [filteredNodes, setFilteredNodes] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedUri, setSelectedUri] = useState(null);
  const [nodeData, setNodeData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingNodes, setLoadingNodes] = useState(true);
  const [history, setHistory] = useState([]);
  const containerRef = useRef(null);
  const [dims, setDims] = useState({ w: 700, h: 500 });

  useEffect(() => {
    loadTopNodes();
  }, []);

  useEffect(() => {
    if (!containerRef.current) return;
    const ro = new ResizeObserver(([entry]) => {
      const { width, height } = entry.contentRect;
      setDims({ w: Math.round(width), h: Math.round(height) });
    });
    ro.observe(containerRef.current);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    if (!searchTerm.trim()) {
      setFilteredNodes(topNodes);
    } else {
      const q = searchTerm.toLowerCase();
      setFilteredNodes(topNodes.filter(n =>
        n.label.toLowerCase().includes(q) ||
        n.id.toLowerCase().includes(q) ||
        (n.types || []).some(t => t.toLowerCase().includes(q))
      ));
    }
  }, [searchTerm, topNodes]);

  const loadTopNodes = async () => {
    setLoadingNodes(true);
    try {
      const res = await fetch(`${API_BASE}/graphdb/top-nodes?limit=200`);
      if (res.ok) {
        const data = await res.json();
        setTopNodes(data.nodes || []);
        setFilteredNodes(data.nodes || []);
      }
    } catch (err) {
      console.error('Failed to load top nodes:', err);
    } finally {
      setLoadingNodes(false);
    }
  };

  const expandNode = useCallback(async (uri) => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/graphdb/node-triples?uri=${encodeURIComponent(uri)}`);
      if (res.ok) {
        const data = await res.json();
        if (selectedUri) {
          setHistory(prev => [...prev, { uri: selectedUri, label: nodeData?.label || selectedUri }]);
        }
        setSelectedUri(uri);
        setNodeData(data);
        if (onNodeClick) onNodeClick({ id: uri, uri, label: data.label });
      }
    } catch (err) {
      console.error('Failed to expand node:', err);
    } finally {
      setLoading(false);
    }
  }, [selectedUri, nodeData, onNodeClick]);

  const goBack = () => {
    if (history.length === 0) {
      setSelectedUri(null);
      setNodeData(null);
      return;
    }
    const prev = history[history.length - 1];
    setHistory(h => h.slice(0, -1));
    setSelectedUri(prev.uri);
    setLoading(true);
    fetch(`${API_BASE}/graphdb/node-triples?uri=${encodeURIComponent(prev.uri)}`)
      .then(r => r.json())
      .then(d => { setNodeData(d); setLoading(false); })
      .catch(() => setLoading(false));
  };

  // Group top nodes by namespace type
  const groupedNodes = {};
  filteredNodes.forEach(n => {
    const group = (n.types && n.types[0]) || 'Other';
    if (!groupedNodes[group]) groupedNodes[group] = [];
    groupedNodes[group].push(n);
  });

  if (!selectedUri) {
    return (
      <div className="h-full w-full flex flex-col bg-nexus-800 rounded-lg border border-nexus-600 overflow-hidden">
        {/* Header */}
        <div className="flex-shrink-0 px-4 pt-4 pb-2">
          <h3 className="text-xs font-mono text-nexus-accent uppercase tracking-widest mb-2">
            Knowledge Graph Explorer
          </h3>
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              placeholder="Search entities by name, type, or URI..."
              className="w-full bg-nexus-900/50 text-slate-200 placeholder:text-slate-500 border border-nexus-700 rounded-lg py-2 pl-9 pr-4 focus:outline-none focus:border-nexus-accent/50 text-sm"
            />
          </div>
          <p className="text-[10px] text-slate-600 mt-1.5 font-mono">
            {filteredNodes.length} entities • Click to explore triples
          </p>
        </div>

        {/* Entity list */}
        <div className="flex-1 overflow-y-auto px-4 pb-4 custom-scrollbar space-y-3">
          {loadingNodes ? (
            <div className="flex items-center justify-center h-40">
              <Loader2 size={20} className="animate-spin text-nexus-accent" />
            </div>
          ) : Object.keys(groupedNodes).length === 0 ? (
            <div className="flex flex-col items-center justify-center h-40 text-slate-500">
              <Database size={32} className="mb-2 opacity-20" />
              <p className="text-sm">No entities found</p>
            </div>
          ) : (
            Object.entries(groupedNodes).sort(([a], [b]) => a.localeCompare(b)).map(([type, nodes]) => (
              <div key={type}>
                <p className="text-[10px] font-mono text-slate-500 uppercase tracking-wider mb-1">{type} ({nodes.length})</p>
                <div className="space-y-1">
                  {nodes.map((n) => (
                    <button
                      key={n.uri}
                      onClick={() => expandNode(n.uri)}
                      className="w-full text-left flex items-center gap-2 px-3 py-2 bg-nexus-900/30 border border-nexus-700/50 rounded-lg hover:border-nexus-accent/40 hover:bg-nexus-900/60 transition-all group"
                    >
                      <span
                        className="w-2 h-2 rounded-full flex-shrink-0"
                        style={{ backgroundColor: nsColor(n.ns) }}
                      />
                      <span className="text-sm text-slate-300 group-hover:text-white truncate flex-1">
                        {n.label}
                      </span>
                      <ChevronRight size={14} className="text-slate-600 group-hover:text-nexus-accent flex-shrink-0 transition-colors" />
                    </button>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    );
  }

  // Expanded node view
  const triples = nodeData?.triples || [];

  return (
    <div className="h-full w-full flex flex-col bg-nexus-800 rounded-lg border border-nexus-600 overflow-hidden">
      {/* Header with breadcrumb */}
      <div className="flex-shrink-0 px-4 pt-3 pb-2 border-b border-nexus-700/50">
        <div className="flex items-center gap-2">
          <button onClick={goBack} className="p-1 rounded hover:bg-nexus-700 text-slate-400 hover:text-white transition-colors">
            <ArrowLeft size={16} />
          </button>
          <div className="flex items-center gap-1 text-[10px] font-mono text-slate-500 overflow-hidden">
            <button onClick={() => { setSelectedUri(null); setNodeData(null); setHistory([]); }}
              className="hover:text-nexus-accent transition-colors flex-shrink-0">
              Entities
            </button>
            {history.map((h, i) => (
              <React.Fragment key={i}>
                <span className="text-slate-700">/</span>
                <button
                  onClick={() => {
                    const uri = h.uri;
                    setHistory(prev => prev.slice(0, i));
                    setSelectedUri(uri);
                    setLoading(true);
                    fetch(`${API_BASE}/graphdb/node-triples?uri=${encodeURIComponent(uri)}`)
                      .then(r => r.json())
                      .then(d => { setNodeData(d); setLoading(false); })
                      .catch(() => setLoading(false));
                  }}
                  className="hover:text-nexus-accent transition-colors truncate max-w-[80px]"
                  title={h.label}
                >
                  {h.label}
                </button>
              </React.Fragment>
            ))}
            <span className="text-slate-700">/</span>
            <span className="text-nexus-accent truncate">{nodeData?.label || '...'}</span>
          </div>
        </div>
        <p className="text-[10px] text-slate-600 font-mono mt-1 truncate" title={selectedUri}>
          {selectedUri}
        </p>
      </div>

      {/* Graph visualization area */}
      <div ref={containerRef} className="flex-1 min-h-0 relative">
        {loading ? (
          <div className="absolute inset-0 flex items-center justify-center">
            <Loader2 size={24} className="animate-spin text-nexus-accent" />
          </div>
        ) : triples.length === 0 ? (
          <div className="absolute inset-0 flex items-center justify-center text-slate-500">
            <p className="text-sm">No triples found for this resource</p>
          </div>
        ) : (
          <NodeGraph
            node={nodeData}
            triples={triples}
            onExpandUri={expandNode}
            containerWidth={dims.w}
            containerHeight={dims.h}
          />
        )}
      </div>

      {/* Triple list (scrollable) */}
      {triples.length > 0 && (
        <div className="flex-shrink-0 border-t border-nexus-700/50 max-h-[180px] overflow-y-auto custom-scrollbar">
          <table className="w-full text-[11px] font-mono">
            <thead className="sticky top-0 bg-nexus-800 z-10">
              <tr className="text-slate-500 text-left">
                <th className="px-3 py-1.5 font-normal">Predicate</th>
                <th className="px-3 py-1.5 font-normal">Value</th>
              </tr>
            </thead>
            <tbody>
              {triples.map((t, i) => (
                <tr key={i} className="border-t border-nexus-700/30 hover:bg-nexus-900/40">
                  <td className="px-3 py-1 text-slate-400 whitespace-nowrap">{t.predicate}</td>
                  <td className="px-3 py-1">
                    {t.isUri ? (
                      <button
                        onClick={() => expandNode(t.rawValue)}
                        className="text-teal-400 hover:text-teal-200 hover:underline flex items-center gap-1"
                      >
                        {t.value}
                        <ExternalLink size={10} className="opacity-50" />
                      </button>
                    ) : (
                      <span className="text-slate-300">{t.value}</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default KnowledgeGraph;
