import React, { useCallback, useEffect, useState, useRef, useMemo } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { Database } from 'lucide-react';

// ── Namespace palette ────────────────────────────────────────────────────────
const NS_COLORS = {
  s223:    '#a855f7',
  brick:   '#22c55e',
  ifc:     '#3b82f6',
  ifcid:   '#60a5fa',
  co:      '#f59e0b',
  bldg:    '#34d399',
  qudt:    '#06b6d4',
  qk:      '#06b6d4',
  rig:     '#ec4899',
  skos:    '#facc15',
  rdfs:    '#94a3b8',
  rdf:     '#94a3b8',
  other:   '#64748b',
};

const PRED_COLORS = {
  'rdf:type':       '#6b7280',
  'rdfs:label':     '#6b7280',
  'skos:exactMatch':'#eab308',
};

// ── Node sizing ──────────────────────────────────────────────────────────────
function nodeSize(node) {
  if (node.kind === 'class')   return 10;
  if (node.kind === 'literal') return 0;   // drawn via canvas, not val
  return 7;
}

// ── Legend items ──────────────────────────────────────────────────────────────
const LEGEND = [
  { label: 'Resource (instance)', shape: 'circle', color: '#60a5fa' },
  { label: 'Class (rdf:type target)', shape: 'hexagon', color: '#a855f7' },
  { label: 'Literal value', shape: 'rect', color: '#334155' },
  { sep: true },
  { label: 's223:', color: NS_COLORS.s223 },
  { label: 'brick:', color: NS_COLORS.brick },
  { label: 'ifc:', color: NS_COLORS.ifc },
  { label: 'overlay (skos)', color: NS_COLORS.skos },
];

// ── Component ────────────────────────────────────────────────────────────────
const KnowledgeGraph = ({ data, onNodeClick }) => {
  const [graphData, setGraphData] = useState(data);
  const containerRef = useRef(null);
  const [dims, setDims] = useState({ w: 800, h: 600 });

  useEffect(() => { setGraphData(data); }, [data]);

  useEffect(() => {
    if (!containerRef.current) return;
    const ro = new ResizeObserver(([entry]) => {
      const { width, height } = entry.contentRect;
      setDims({ w: Math.round(width), h: Math.round(height) });
    });
    ro.observe(containerRef.current);
    return () => ro.disconnect();
  }, []);

  const handleNodeClick = useCallback(
    (node) => onNodeClick(node),
    [onNodeClick],
  );

  // ── Custom node renderer ──────────────────────────────────────────────────
  const drawNode = useCallback((node, ctx, globalScale) => {
    const kind = node.kind || 'resource';
    const ns   = node.ns || 'other';
    const color = NS_COLORS[ns] || NS_COLORS.other;

    if (kind === 'literal') {
      // ── Rectangle for literal values ──────────────────────────────────
      const fontSize = Math.max(9 / globalScale, 2);
      ctx.font = `${fontSize}px "SF Mono", Menlo, monospace`;
      const text = node.label || '""';
      const tw = ctx.measureText(text).width;
      const pad = 3 / globalScale;
      const hw = tw / 2 + pad;
      const hh = fontSize / 2 + pad;

      ctx.fillStyle = '#1e293b';
      ctx.strokeStyle = '#475569';
      ctx.lineWidth = 0.6 / globalScale;
      ctx.beginPath();
      ctx.rect(node.x - hw, node.y - hh, hw * 2, hh * 2);
      ctx.fill();
      ctx.stroke();

      ctx.fillStyle = '#cbd5e1';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(text, node.x, node.y);
      return;
    }

    if (kind === 'class') {
      // ── Hexagon for class / type nodes ────────────────────────────────
      const r = 10;
      ctx.beginPath();
      for (let i = 0; i < 6; i++) {
        const a = (Math.PI / 3) * i - Math.PI / 6;
        const px = node.x + r * Math.cos(a);
        const py = node.y + r * Math.sin(a);
        i === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py);
      }
      ctx.closePath();
      ctx.fillStyle = color;
      ctx.globalAlpha = 0.85;
      ctx.fill();
      ctx.globalAlpha = 1;
      ctx.strokeStyle = 'rgba(255,255,255,0.35)';
      ctx.lineWidth = 1.2;
      ctx.stroke();

      // Inner hexagon (double-border convention for classes)
      const r2 = 6.5;
      ctx.beginPath();
      for (let i = 0; i < 6; i++) {
        const a = (Math.PI / 3) * i - Math.PI / 6;
        const px = node.x + r2 * Math.cos(a);
        const py = node.y + r2 * Math.sin(a);
        i === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py);
      }
      ctx.closePath();
      ctx.strokeStyle = 'rgba(255,255,255,0.15)';
      ctx.lineWidth = 0.6;
      ctx.stroke();

      // Class label (always shown)
      const fs = Math.max(9 / globalScale, 2.5);
      ctx.font = `600 ${fs}px Inter, system-ui, sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      ctx.fillStyle = 'rgba(255,255,255,0.92)';
      ctx.fillText(node.label || '', node.x, node.y + r + 2);
      return;
    }

    // ── Circle for resource (instance) nodes ────────────────────────────
    const radius = 6;
    ctx.beginPath();
    ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI);
    ctx.fillStyle = color;
    ctx.globalAlpha = 0.9;
    ctx.fill();
    ctx.globalAlpha = 1;
    ctx.strokeStyle = 'rgba(255,255,255,0.18)';
    ctx.lineWidth = 0.6;
    ctx.stroke();

    // Resource label
    if (globalScale > 0.45) {
      const fs = Math.max(8 / globalScale, 2);
      ctx.font = `${fs}px Inter, system-ui, sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      ctx.fillStyle = 'rgba(255,255,255,0.7)';
      ctx.fillText(node.label || '', node.x, node.y + radius + 1.5);
    }
  }, []);

  // ── Custom link renderer (predicate labels + dashed rdf:type) ─────────
  const drawLink = useCallback((link, ctx, globalScale) => {
    const src = link.source;
    const tgt = link.target;
    if (!src || !tgt || src.x == null || tgt.x == null) return;

    const pred = link.predicate || '';
    const isType  = pred === 'rdf:type';
    const isLabel = pred === 'rdfs:label';
    const isSkos  = pred.startsWith('skos:');

    // Line style
    ctx.beginPath();
    ctx.moveTo(src.x, src.y);
    ctx.lineTo(tgt.x, tgt.y);

    if (isType || isLabel) {
      ctx.setLineDash([3, 3]);
      ctx.strokeStyle = '#4b5563';
      ctx.lineWidth = 0.6;
    } else if (isSkos) {
      ctx.setLineDash([]);
      ctx.strokeStyle = '#eab308';
      ctx.lineWidth = 1.8;
    } else {
      ctx.setLineDash([]);
      ctx.strokeStyle = PRED_COLORS[pred] || '#334155';
      ctx.lineWidth = 1;
    }
    ctx.stroke();
    ctx.setLineDash([]);

    // Arrow head
    const dx = tgt.x - src.x;
    const dy = tgt.y - src.y;
    const len = Math.sqrt(dx * dx + dy * dy);
    if (len < 1) return;
    const ux = dx / len, uy = dy / len;
    const arrowLen = 5;
    const arrowW   = 2.5;
    const tipX = tgt.x - ux * 8;
    const tipY = tgt.y - uy * 8;
    ctx.beginPath();
    ctx.moveTo(tipX, tipY);
    ctx.lineTo(tipX - ux * arrowLen + uy * arrowW, tipY - uy * arrowLen - ux * arrowW);
    ctx.lineTo(tipX - ux * arrowLen - uy * arrowW, tipY - uy * arrowLen + ux * arrowW);
    ctx.closePath();
    ctx.fillStyle = isSkos ? '#eab308' : (isType ? '#4b5563' : '#475569');
    ctx.fill();

    // Predicate label at midpoint
    if (globalScale > 0.55) {
      const mx = (src.x + tgt.x) / 2;
      const my = (src.y + tgt.y) / 2;
      const fs = Math.max(7 / globalScale, 1.8);
      ctx.font = `${fs}px "SF Mono", Menlo, monospace`;
      const tw = ctx.measureText(pred).width;

      ctx.fillStyle = 'rgba(10, 15, 25, 0.75)';
      ctx.fillRect(mx - tw / 2 - 2, my - fs / 2 - 1, tw + 4, fs + 2);

      ctx.fillStyle = isSkos ? '#fde047' : (isType ? '#9ca3af' : '#94a3b8');
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(pred, mx, my);
    }
  }, []);

  // ── Stats ──────────────────────────────────────────────────────────────
  const stats = useMemo(() => {
    if (!graphData?.nodes) return null;
    const resources = graphData.nodes.filter(n => n.kind === 'resource').length;
    const classes   = graphData.nodes.filter(n => n.kind === 'class').length;
    const literals  = graphData.nodes.filter(n => n.kind === 'literal').length;
    return { resources, classes, literals, edges: graphData.links?.length || 0 };
  }, [graphData]);

  // ── Empty state ────────────────────────────────────────────────────────
  if (!graphData || !graphData.nodes || graphData.nodes.length === 0) {
    return (
      <div className="h-full w-full flex flex-col items-center justify-center text-slate-500 bg-nexus-800 rounded-lg border border-nexus-600">
        <Database size={48} className="mb-4 opacity-20" />
        <p className="font-mono text-sm">No graph data available</p>
        <p className="text-xs mt-2 text-slate-600">Waiting for GraphDB connection...</p>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="relative w-full h-full bg-nexus-800 rounded-lg overflow-hidden border border-nexus-600 shadow-inner"
    >
      {/* Legend + stats */}
      <div className="absolute top-2 left-3 z-10 pointer-events-none select-none">
        <h3 className="text-xs font-mono text-nexus-accent uppercase tracking-widest">
          RDF Knowledge Graph
        </h3>

        <div className="flex gap-3 mt-1.5 flex-wrap">
          {LEGEND.map((item, i) =>
            item.sep ? (
              <span key={i} className="w-px h-3 bg-nexus-700 self-center" />
            ) : (
              <span key={i} className="flex items-center text-[10px] text-slate-400 gap-1">
                {item.shape === 'hexagon' ? (
                  <svg width="9" height="9" viewBox="-5 -5 10 10">
                    <polygon
                      points={[...Array(6)].map((_, j) => {
                        const a = (Math.PI / 3) * j - Math.PI / 6;
                        return `${4 * Math.cos(a)},${4 * Math.sin(a)}`;
                      }).join(' ')}
                      fill={item.color}
                    />
                  </svg>
                ) : item.shape === 'rect' ? (
                  <span className="w-3 h-2 rounded-[1px] border border-slate-500" style={{ background: item.color }} />
                ) : item.shape === 'circle' ? (
                  <span className="w-2 h-2 rounded-full" style={{ background: item.color }} />
                ) : (
                  <span className="w-2 h-2 rounded-full" style={{ background: item.color }} />
                )}
                {item.label}
              </span>
            ),
          )}
        </div>

        {stats && (
          <p className="text-[10px] text-slate-600 mt-1 font-mono">
            {stats.resources} resources &middot; {stats.classes} classes &middot;{' '}
            {stats.literals} literals &middot; {stats.edges} triples
          </p>
        )}
      </div>

      <ForceGraph2D
        graphData={graphData}
        nodeCanvasObject={drawNode}
        nodePointerAreaPaint={(node, color, ctx) => {
          const s = node.kind === 'literal' ? 12 : 10;
          ctx.fillStyle = color;
          ctx.beginPath();
          ctx.arc(node.x, node.y, s, 0, 2 * Math.PI);
          ctx.fill();
        }}
        nodeLabel={(node) => {
          const lines = [node.label || node.id];
          if (node.kind === 'resource' && node.rdfTypes?.length) {
            lines.push(`a ${node.rdfTypes.join(', ')}`);
          }
          if (node.kind === 'class') lines.push('[Class]');
          if (node.kind === 'literal') lines.push('[Literal]');
          return lines.join('\n');
        }}
        linkCanvasObjectMode={() => 'replace'}
        linkCanvasObject={drawLink}
        linkPointerAreaPaint={(link, color, ctx) => {
          const s = link.source, t = link.target;
          if (!s || !t || s.x == null) return;
          ctx.strokeStyle = color;
          ctx.lineWidth = 6;
          ctx.beginPath();
          ctx.moveTo(s.x, s.y);
          ctx.lineTo(t.x, t.y);
          ctx.stroke();
        }}
        onNodeClick={handleNodeClick}
        backgroundColor="rgba(0,0,0,0)"
        width={dims.w}
        height={dims.h}
        cooldownTicks={150}
        d3AlphaDecay={0.015}
        d3VelocityDecay={0.25}
        d3AlphaMin={0.001}
      />
    </div>
  );
};

export default KnowledgeGraph;
