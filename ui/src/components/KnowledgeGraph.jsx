import React, { useEffect, useMemo, useState } from 'react';
import {
  ChevronRight,
  ChevronDown,
  ArrowLeft,
  Loader2,
  Network,
  Search,
  FolderTree,
} from 'lucide-react';
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
  if (node?.type === 'class') return '#f59e0b';
  if (node?.type === 'literal') return '#94a3b8';
  return NS_COLORS[node?.ns] || NS_COLORS.other;
}

function TypeBadge({ text }) {
  if (!text) return null;
  return (
    <span className="inline-flex items-center rounded-md border border-nexus-700 bg-nexus-900/70 px-1.5 py-0.5 text-[10px] font-mono text-slate-400">
      {text}
    </span>
  );
}

function prettyLabel(node) {
  const label = node?.label || node?.name || node?.id || '';
  const type = (node?.type || '').toLowerCase();

  if (label && !/^co:\d+$/i.test(label)) return label;

  if (type.includes('ifcproject')) return 'CASE Project';
  if (type.includes('ifcsite')) return 'Site';
  if (type.includes('ifcbuilding')) return 'Building';

  if (type.includes('ifcbuildingstorey')) {
    if (node?.id?.endsWith('#46')) return 'Storey 1';
    if (node?.id?.endsWith('#50')) return 'Storey 2';
    if (node?.id?.endsWith('#54')) return 'Storey 3';
    return 'Storey';
  }

  if (type.includes('ifcspace')) return 'Space';

  return label;
}

function TreeRow({
  node,
  depth = 0,
  expandedIds,
  loadingIds,
  loadedChildren,
  searchTerm,
  onToggle,
  onSelect,
  selectedId,
}) {
  const hasChildren = loadedChildren[node.id] ? loadedChildren[node.id].length > 0 : true;
  const isExpanded = expandedIds.has(node.id);
  const isLoading = loadingIds.has(node.id);
  const children = loadedChildren[node.id] || [];

  return (
    <div>
      <div
        className={`group flex items-center gap-2 rounded-lg px-2 py-1.5 transition-all ${
          selectedId === node.id
            ? 'bg-nexus-900 border border-nexus-accent/40'
            : 'border border-transparent hover:bg-nexus-900/60'
        }`}
        style={{ marginLeft: depth * 16 }}
      >
        <button
          onClick={() => onToggle(node)}
          className="flex h-5 w-5 items-center justify-center rounded text-slate-500 hover:bg-nexus-700 hover:text-white transition-colors"
          title="Expand"
        >
          {isLoading ? (
            <Loader2 size={12} className="animate-spin" />
          ) : isExpanded ? (
            <ChevronDown size={14} />
          ) : (
            <ChevronRight size={14} />
          )}
        </button>

        <button
          onClick={() => onSelect(node)}
          className="flex min-w-0 flex-1 items-center gap-2 text-left"
        >
          <span
            className="h-2.5 w-2.5 flex-shrink-0 rounded-full"
            style={{ backgroundColor: getNodeColor(node) }}
          />
          <div className="min-w-0 flex-1">
            <div className="truncate text-sm text-slate-200 group-hover:text-white">
              {prettyLabel(node)}
            </div>
            <div className="flex items-center gap-2 mt-0.5">
              {node.type && <TypeBadge text={node.type} />}
              {node.rel && <TypeBadge text={node.rel} />}
            </div>
          </div>
        </button>
      </div>

      {isExpanded && children.length > 0 && (
        <div className="mt-1 space-y-1">
          {children
            .filter((child) => {
              if (!searchTerm.trim()) return true;
              const q = searchTerm.toLowerCase();
              return (
                (child.label || '').toLowerCase().includes(q) ||
                (child.id || '').toLowerCase().includes(q) ||
                (child.type || '').toLowerCase().includes(q)
              );
            })
            .map((child) => (
              <TreeRow
                key={child.id}
                node={child}
                depth={depth + 1}
                expandedIds={expandedIds}
                loadingIds={loadingIds}
                loadedChildren={loadedChildren}
                searchTerm={searchTerm}
                onToggle={onToggle}
                onSelect={onSelect}
                selectedId={selectedId}
              />
            ))}
        </div>
      )}
    </div>
  );
}

function radialPositions(cx, cy, count, radius) {
  if (count === 0) return [];
  const positions = [];
  const startAngle = -Math.PI / 2;
  const sweep = Math.PI * 1.4;
  for (let i = 0; i < count; i++) {
    const angle =
      startAngle +
      (count === 1 ? 0 : (sweep * i) / (count - 1)) -
      sweep / 2 +
      Math.PI / 2;

    positions.push({
      x: cx + radius * Math.cos(angle),
      y: cy + radius * Math.sin(angle),
    });
  }
  return positions;
}

function RadialInspector({ centerNode, edges, nodesById, onSelectNode }) {
  const width = 1400;
  const height = 900;
  const cx = 240;
  const cy = height / 2;
  const radius = 380;

  const triples = edges.map((e) => {
    const target = nodesById[e.target];
    return {
      predicate: e.predicate,
      target,
      clickable: target && !String(target.id).startsWith('_:') && target.type !== 'literal',
    };
  });

  const positions = radialPositions(cx, cy, triples.length, radius);

  return (
    <div className="w-full h-full overflow-auto">
      <div className="min-w-[1400px] min-h-[900px] bg-white">
        <svg width={width} height={height}>
          {triples.map((t, i) => {
            const pos = positions[i];
            const target = t.target;
            const label = target?.label || target?.name || 'Unknown';
            const predicateLabel = t.predicate || '';

            return (
              <g key={`${predicateLabel}-${target?.id || i}`}>
                <line
                  x1={cx}
                  y1={cy}
                  x2={pos.x}
                  y2={pos.y}
                  stroke="#cbd5e1"
                  strokeWidth="1.5"
                />

                <text
                  x={(cx + pos.x) / 2 - 8}
                  y={(cy + pos.y) / 2 - 6}
                  textAnchor="end"
                  fontSize="13"
                  fill="#444"
                >
                  {predicateLabel}
                </text>

                <circle
                  cx={pos.x}
                  cy={pos.y}
                  r={8}
                  fill={target?.type === 'literal' ? '#ffffff' : '#e0f2fe'}
                  stroke="#4fd1c5"
                  strokeWidth="2"
                  style={{ cursor: t.clickable ? 'pointer' : 'default' }}
                  onClick={() => t.clickable && onSelectNode(target)}
                />

                <text
                  x={pos.x + 14}
                  y={pos.y + 4}
                  textAnchor="start"
                  fontSize="14"
                  fill={t.clickable ? '#222' : '#444'}
                  style={{ cursor: t.clickable ? 'pointer' : 'default' }}
                  onClick={() => t.clickable && onSelectNode(target)}
                >
                  {label.length > 42 ? `${label.slice(0, 39)}...` : label}
                </text>
              </g>
            );
          })}

          <circle
            cx={cx}
            cy={cy}
            r={16}
            fill="#fff7ed"
            stroke="#f59e0b"
            strokeWidth="3"
          />

          <text
            x={cx - 24}
            y={cy + 34}
            textAnchor="start"
            fontSize="18"
            fill="#222"
            fontWeight="600"
          >
            {centerNode?.label || centerNode?.name || 'Selected Node'}
          </text>
        </svg>
      </div>
    </div>
  );
}

const KnowledgeGraph = ({ onNodeClick }) => {
  const [root, setRoot] = useState(null);
  const [expandedIds, setExpandedIds] = useState(new Set());
  const [loadingIds, setLoadingIds] = useState(new Set());
  const [loadedChildren, setLoadedChildren] = useState({});
  const [selected, setSelected] = useState(null);
  const [focusedGraph, setFocusedGraph] = useState(null);
  const [loadingRoot, setLoadingRoot] = useState(true);
  const [loadingFocus, setLoadingFocus] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [navHistory, setNavHistory] = useState([]);

  useEffect(() => {
    loadRoot();
  }, []);

  const loadRoot = async () => {
    setLoadingRoot(true);
    try {
      const res = await fetch(`${API_BASE}/graphdb/tree/root`);
      const data = await res.json();
  
      setRoot(data);
      setSelected(data);
      await loadFocus(data.id, false);
  
      const expanded = new Set([data.id]);
      const nextLoadedChildren = {};
  
      const rootChildren = await fetchChildren(data.id);
      nextLoadedChildren[data.id] = rootChildren;
  
      if (rootChildren.length > 0) {
        const siteNode = rootChildren[0];
        expanded.add(siteNode.id);
  
        const siteChildren = await fetchChildren(siteNode.id);
        nextLoadedChildren[siteNode.id] = siteChildren;
  
        if (siteChildren.length > 0) {
          const buildingNode = siteChildren[0];
          expanded.add(buildingNode.id);
  
          const buildingChildren = await fetchChildren(buildingNode.id);
          nextLoadedChildren[buildingNode.id] = buildingChildren;
        }
      }
  
      setLoadedChildren(nextLoadedChildren);
      setExpandedIds(expanded);
    } catch (err) {
      console.error('Failed to load tree root:', err);
      setRoot(null);
    } finally {
      setLoadingRoot(false);
    }
  };

  const fetchChildren = async (nodeId) => {
    const res = await fetch(`${API_BASE}/graphdb/tree/children?uri=${encodeURIComponent(nodeId)}`);
    if (!res.ok) throw new Error('Failed to fetch children');
    const data = await res.json();
    return data.children || [];
  };

  const loadFocus = async (uri, pushHistory = true) => {
    setLoadingFocus(true);
    try {
      const res = await fetch(`${API_BASE}/graphdb/focus?uri=${encodeURIComponent(uri)}&limit=40`);
      const data = await res.json();

      const centerNode =
        data.nodes?.find((n) => n.id === uri) || {
          id: uri,
          label: uri,
          name: uri,
        };

      if (pushHistory && selected?.id && selected.id !== uri) {
        setNavHistory((prev) => [...prev, selected]);
      }

      const nextSelected = {
        id: uri,
        uri,
        label: centerNode.label || centerNode.name || uri,
        name: centerNode.name || centerNode.label || uri,
        type: centerNode.type || '',
        ns: centerNode.ns || 'other',
      };

      setSelected(nextSelected);
      setFocusedGraph(data);

      if (onNodeClick) {
        onNodeClick({
          id: uri,
          uri,
          label: nextSelected.label,
          type: nextSelected.type,
        });
      }
    } catch (err) {
      console.error('Failed to load focused graph:', err);
    } finally {
      setLoadingFocus(false);
    }
  };

  const toggleNode = async (node) => {
    const nodeId = node.id;

    if (expandedIds.has(nodeId)) {
      const next = new Set(expandedIds);
      next.delete(nodeId);
      setExpandedIds(next);
      return;
    }

    if (!loadedChildren[nodeId]) {
      const nextLoading = new Set(loadingIds);
      nextLoading.add(nodeId);
      setLoadingIds(nextLoading);

      try {
        const children = await fetchChildren(nodeId);
        setLoadedChildren((prev) => ({
          ...prev,
          [nodeId]: children,
        }));
      } catch (err) {
        console.error(`Failed to load children for ${nodeId}:`, err);
        setLoadedChildren((prev) => ({
          ...prev,
          [nodeId]: [],
        }));
      } finally {
        setLoadingIds((prev) => {
          const copy = new Set(prev);
          copy.delete(nodeId);
          return copy;
        });
      }
    }

    setExpandedIds((prev) => {
      const copy = new Set(prev);
      copy.add(nodeId);
      return copy;
    });
  };

  const handleSelectNode = async (node) => {
    await loadFocus(node.id, true);
  };

  const goBack = async () => {
    if (navHistory.length === 0) return;
    const prev = navHistory[navHistory.length - 1];
    setNavHistory((h) => h.slice(0, -1));
    await loadFocus(prev.id, false);
  };

  const groupedEdges = useMemo(() => {
    const edges = focusedGraph?.edges || [];
    const nodesById = Object.fromEntries((focusedGraph?.nodes || []).map((n) => [n.id, n]));

    const groups = {
      identity: [],
      hierarchy: [],
      semantics: [],
      properties: [],
      other: [],
    };

    edges.forEach((e, i) => {
      const target = nodesById[e.target];
      const row = {
        key: `${e.source}-${e.target}-${e.predicate}-${i}`,
        edge: e,
        target,
      };

      const p = (e.predicate || '').toLowerCase();

      if (p.includes('label') || p.includes('type') || p === 'rdf:type') {
        groups.identity.push(row);
      } else if (
        p.includes('part') ||
        p.includes('zone') ||
        p.includes('location') ||
        p.includes('decomposes')
      ) {
        groups.hierarchy.push(row);
      } else if (
        p.includes('exactmatch') ||
        p.includes('observes') ||
        p.includes('point')
      ) {
        groups.semantics.push(row);
      } else if (target?.type === 'literal') {
        groups.properties.push(row);
      } else {
        groups.other.push(row);
      }
    });

    return groups;
  }, [focusedGraph]);

  if (loadingRoot) {
    return (
      <div className="h-full w-full flex items-center justify-center bg-nexus-800 rounded-lg border border-nexus-600">
        <Loader2 size={24} className="animate-spin text-nexus-accent" />
      </div>
    );
  }

  if (!root) {
    return (
      <div className="h-full w-full flex items-center justify-center bg-nexus-800 rounded-lg border border-nexus-600 text-slate-500">
        No project root found.
      </div>
    );
  }

  const center = focusedGraph?.nodes?.find((n) => n.id === focusedGraph.center);
  const renderGroup = (title, rows) => {
    if (!rows || rows.length === 0) return null;

    return (
      <div className="space-y-2">
        <div className="text-[10px] uppercase tracking-widest font-mono text-slate-500">
          {title}
        </div>
        {rows.map(({ key, edge, target }) => {
          const clickable =
            target && !String(target.id).startsWith('_:') && target.type !== 'literal';

          return (
            <div
              key={key}
              className="flex items-center gap-3 rounded-xl border border-nexus-700/40 bg-nexus-900/30 p-3"
            >
              <div className="min-w-[150px] text-[11px] font-mono text-nexus-accent">
                {edge.predicate}
              </div>

              <div className="text-slate-500">→</div>

              {target ? (
                clickable ? (
                  <button
                    onClick={() => handleSelectNode(target)}
                    className="flex items-center gap-2 rounded-lg px-2 py-1 text-left hover:bg-nexus-800/60 transition-colors"
                  >
                    <span
                      className="h-2.5 w-2.5 rounded-full"
                      style={{ backgroundColor: getNodeColor(target) }}
                    />
                    <div>
                      <div className="text-sm text-white">
                        {target.label || target.name}
                      </div>
                      <div className="max-w-[420px] truncate text-[10px] font-mono text-slate-500">
                        {target.id}
                      </div>
                    </div>
                  </button>
                ) : (
                  <div className="flex items-center gap-2 px-2 py-1">
                    <span
                      className="h-2.5 w-2.5 rounded-full"
                      style={{ backgroundColor: getNodeColor(target) }}
                    />
                    <div>
                      <div className="text-sm text-slate-200">
                        {target.label || target.name}
                      </div>
                      <div className="max-w-[420px] truncate text-[10px] font-mono text-slate-500">
                        {target.id}
                      </div>
                    </div>
                  </div>
                )
              ) : (
                <div className="text-sm text-slate-400">Unknown target</div>
              )}
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div className="h-full w-full bg-nexus-800 rounded-lg border border-nexus-600 overflow-hidden">
      <div className="grid h-full grid-cols-[360px_1fr]">
        {/* Left tree pane */}
        <div className="border-r border-nexus-700/50 flex flex-col min-h-0">
          <div className="flex-shrink-0 px-4 pt-4 pb-3 border-b border-nexus-700/50">
            <div className="flex items-center gap-2 mb-2">
              <FolderTree size={16} className="text-nexus-accent" />
              <h3 className="text-xs font-mono text-nexus-accent uppercase tracking-widest">
                CASE Hierarchy
              </h3>
            </div>

            <div className="relative">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search visible tree..."
                className="w-full bg-nexus-900/50 text-slate-200 placeholder:text-slate-500 border border-nexus-700 rounded-lg py-2 pl-9 pr-4 focus:outline-none focus:border-nexus-accent/50 text-sm"
              />
            </div>

            <p className="text-[10px] text-slate-600 mt-2 font-mono">
              Start from one root and expand downward
            </p>
          </div>

          <div className="flex-1 overflow-auto p-3 custom-scrollbar">
            <TreeRow
              node={root}
              depth={0}
              expandedIds={expandedIds}
              loadingIds={loadingIds}
              loadedChildren={loadedChildren}
              searchTerm={searchTerm}
              onToggle={toggleNode}
              onSelect={handleSelectNode}
              selectedId={selected?.id}
            />
          </div>
        </div>

        {/* Right detail pane */}
        <div className="flex flex-col min-h-0">
          <div className="flex-shrink-0 px-4 pt-3 pb-2 border-b border-nexus-700/50">
            <div className="flex items-center gap-2">
              <button
                onClick={goBack}
                disabled={navHistory.length === 0}
                className="p-1 rounded hover:bg-nexus-700 text-slate-400 hover:text-white transition-colors disabled:opacity-30"
              >
                <ArrowLeft size={16} />
              </button>
              <div className="truncate text-sm font-medium text-white">
                {prettyLabel(center || selected)}
              </div>
            </div>
            <p className="truncate mt-1 text-[10px] font-mono text-slate-500">
              {selected?.uri || selected?.id}
            </p>
          </div>

          <div className="flex-1 min-h-0 overflow-hidden">
            {loadingFocus ? (
              <div className="flex items-center justify-center h-full">
                <Loader2 size={20} className="animate-spin text-nexus-accent" />
              </div>
            ) : (
              <RadialInspector
                centerNode={center || selected}
                edges={focusedGraph?.edges || []}
                nodesById={Object.fromEntries((focusedGraph?.nodes || []).map((n) => [n.id, n]))}
                onSelectNode={handleSelectNode}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default KnowledgeGraph;