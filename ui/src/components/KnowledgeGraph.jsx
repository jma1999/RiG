import React, { useEffect, useMemo, useRef, useState } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { Search, RefreshCw, Network } from 'lucide-react';
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

function nodeColor(node) {
  const ns = node.ns || node.properties?.ns || 'other';
  if (node.type === 'literal') return '#94a3b8';
  if (node.type === 'class') return '#f59e0b';
  return NS_COLORS[ns] || NS_COLORS.other;
}

function mergeGraph(base, incoming) {
  const nodeMap = new Map((base.nodes || []).map(n => [n.id, n]));
  const edgeMap = new Map(
    (base.links || []).map(e => [`${e.source}->${e.target}->${e.predicate || e.relationship || e.type}`, e])
  );

  (incoming.nodes || []).forEach(n => {
    nodeMap.set(n.id, {
      ...n,
      label: n.label || n.name || n.id,
      name: n.name || n.label || n.id,
      ns: n.ns || n.properties?.ns || 'other',
    });
  });

  (incoming.links || incoming.edges || []).forEach(e => {
    const source = typeof e.source === 'object' ? e.source.id : e.source;
    const target = typeof e.target === 'object' ? e.target.id : e.target;
    const predicate = e.predicate || e.relationship || e.type || 'related';
    edgeMap.set(`${source}->${target}->${predicate}`, {
      source,
      target,
      predicate,
    });
  });

  return {
    nodes: Array.from(nodeMap.values()),
    links: Array.from(edgeMap.values()),
  };
}

const KnowledgeGraph = ({ data, onNodeClick }) => {
  const fgRef = useRef(null);
  const [graph, setGraph] = useState({ nodes: [], links: [] });
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(false);
  const [selectedNode, setSelectedNode] = useState(null);

  useEffect(() => {
    if (data?.nodes?.length) {
      const normalized = {
        nodes: data.nodes.map(n => ({
          ...n,
          label: n.label || n.name || n.id,
          name: n.name || n.label || n.id,
          ns: n.ns || n.properties?.ns || 'other',
        })),
        links: (data.links || []).map(e => ({
          source: typeof e.source === 'object' ? e.source.id : e.source,
          target: typeof e.target === 'object' ? e.target.id : e.target,
          predicate: e.predicate || e.relationship || e.type || 'related',
        })),
      };
      setGraph(normalized);
      return;
    }

    loadInitialGraph();
  }, [data]);

  const loadInitialGraph = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/graphdb/graph?limit=300`);
      if (!res.ok) throw new Error('Failed to load graph');
      const raw = await res.json();

      setGraph({
        nodes: (raw.nodes || []).map(n => ({
          ...n,
          label: n.label || n.name || n.id,
          name: n.name || n.label || n.id,
          ns: n.ns || n.properties?.ns || 'other',
        })),
        links: (raw.edges || []).map(e => ({
          source: e.source,
          target: e.target,
          predicate: e.type || 'related',
        })),
      });
    } catch (err) {
      console.error('Failed to load graph:', err);
      setGraph({ nodes: [], links: [] });
    } finally {
      setLoading(false);
    }
  };

  const expandNode = async (node) => {
    if (!node?.id || String(node.id).startsWith('_:')) return;

    setSelectedNode(node);
    if (onNodeClick) onNodeClick(node);

    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/graphdb/expand?uri=${encodeURIComponent(node.id)}&limit=120`);
      if (!res.ok) throw new Error('Failed to expand node');

      const raw = await res.json();
      const expanded = {
        nodes: (raw.nodes || []).map(n => ({
          ...n,
          label: n.label || n.name || n.id,
          name: n.name || n.label || n.id,
          ns: n.ns || n.properties?.ns || 'other',
        })),
        links: (raw.edges || []).map(e => ({
          source: e.source,
          target: e.target,
          predicate: e.type || 'related',
        })),
      };

      setGraph(prev => mergeGraph(prev, expanded));
    } catch (err) {
      console.error('Failed to expand node:', err);
    } finally {
      setLoading(false);
    }
  };

  const filteredGraph = useMemo(() => {
    if (!searchTerm.trim()) return graph;

    const q = searchTerm.toLowerCase();
    const matchedIds = new Set(
      graph.nodes
        .filter(n =>
          (n.label || '').toLowerCase().includes(q) ||
          (n.name || '').toLowerCase().includes(q) ||
          (n.id || '').toLowerCase().includes(q)
        )
        .map(n => n.id)
    );

    const links = graph.links.filter(l => matchedIds.has(l.source) || matchedIds.has(l.target));
    links.forEach(l => {
      matchedIds.add(l.source);
      matchedIds.add(l.target);
    });

    return {
      nodes: graph.nodes.filter(n => matchedIds.has(n.id)),
      links,
    };
  }, [graph, searchTerm]);

  return (
    <div className="h-full w-full bg-nexus-800 rounded-lg border border-nexus-600 overflow-hidden flex flex-col">
      <div className="flex items-center justify-between px-4 py-3 border-b border-nexus-700/50">
        <div>
          <h3 className="text-xs font-mono text-nexus-accent uppercase tracking-widest">
            Interactive RDF Graph
          </h3>
          <p className="text-[10px] text-slate-500 font-mono mt-1">
            Click nodes to expand neighborhood • drag to explore • scroll to zoom
          </p>
        </div>

        <button
          onClick={loadInitialGraph}
          className="p-2 hover:bg-nexus-700 rounded-lg transition-colors text-slate-400"
          title="Reload graph"
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>

      <div className="px-4 py-3 border-b border-nexus-700/30">
        <div className="relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Filter visible graph by label or URI..."
            className="w-full bg-nexus-900/50 text-slate-200 placeholder:text-slate-500 border border-nexus-700 rounded-lg py-2 pl-9 pr-4 focus:outline-none focus:border-nexus-accent/50 text-sm"
          />
        </div>
      </div>

      <div className="flex-1 relative">
        {filteredGraph.nodes.length === 0 ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-slate-500">
            <Network size={36} className="mb-3 opacity-30" />
            <p className="text-sm">No graph data loaded</p>
          </div>
        ) : (
          <ForceGraph2D
            ref={fgRef}
            graphData={filteredGraph}
            backgroundColor="#111827"
            nodeRelSize={6}
            linkWidth={1}
            linkColor={() => 'rgba(148,163,184,0.35)'}
            cooldownTicks={120}
            onNodeClick={expandNode}
            nodeCanvasObject={(node, ctx, globalScale) => {
              const label = node.label || node.name || node.id;
              const fontSize = Math.max(10 / globalScale, 3);
              const color = nodeColor(node);

              ctx.beginPath();
              ctx.arc(node.x, node.y, node.type === 'literal' ? 4 : 6, 0, 2 * Math.PI, false);
              ctx.fillStyle = color;
              ctx.fill();

              if (selectedNode?.id === node.id) {
                ctx.beginPath();
                ctx.arc(node.x, node.y, 10, 0, 2 * Math.PI, false);
                ctx.strokeStyle = '#00f0ff';
                ctx.lineWidth = 1.5;
                ctx.stroke();
              }

              ctx.font = `${fontSize}px Inter, system-ui, sans-serif`;
              ctx.fillStyle = '#e5e7eb';
              ctx.textAlign = 'left';
              ctx.textBaseline = 'middle';
              ctx.fillText(label.length > 36 ? `${label.slice(0, 33)}...` : label, node.x + 10, node.y);
            }}
            linkLabel={(link) => link.predicate || ''}
          />
        )}

        {loading && (
          <div className="absolute top-3 right-3 bg-nexus-900/90 border border-nexus-700 rounded-md px-3 py-1 text-[11px] font-mono text-slate-300">
            Expanding graph...
          </div>
        )}
      </div>

      <div className="border-t border-nexus-700/50 px-4 py-2 text-[11px] font-mono text-slate-500 flex justify-between">
        <span>{filteredGraph.nodes.length} nodes</span>
        <span>{filteredGraph.links.length} edges</span>
        <span>{selectedNode ? `Selected: ${selectedNode.label || selectedNode.name || selectedNode.id}` : 'No selection'}</span>
      </div>
    </div>
  );
};

export default KnowledgeGraph;