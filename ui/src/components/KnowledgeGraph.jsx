import React, { useCallback, useEffect, useState } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { Database } from 'lucide-react';
import { API_BASE } from "@/lib/env";

const KnowledgeGraph = ({ data, onNodeClick }) => {
  const [graphData, setGraphData] = useState(data);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setGraphData(data);
  }, [data]);

  const handleNodeClick = useCallback((node) => {
    onNodeClick(node);
  }, [onNodeClick]);

  const getNodeColor = (node) => {
    if (node.status === 'warning') return '#ffb020';
    if (node.status === 'critical') return '#ff4d4d';
    // Color by type
    if (node.type && node.type.includes('Equipment')) return '#00f0ff';
    if (node.type && node.type.includes('Point')) return '#00ff9d';
    if (node.type && node.type.includes('Zone')) return '#6366f1';
    if (node.type && node.type.includes('Space')) return '#8b5cf6';
    return '#00f0ff'; // Default accent color
  };

  const getNodeSize = (node) => {
    if (node.type && (node.type.includes('Equipment') || node.type.includes('Asset'))) return 12;
    if (node.type && node.type.includes('Zone')) return 10;
    return 8;
  };

  if (!graphData || !graphData.nodes || graphData.nodes.length === 0) {
    return (
      <div className="h-full w-full flex flex-col items-center justify-center text-slate-500 bg-nexus-800 rounded-lg border border-nexus-600">
        <Database size={48} className="mb-4 opacity-20" />
        <p className="font-mono text-sm">No graph data available</p>
        <p className="text-xs mt-2 text-slate-600">Loading RDF graph from GraphDB repository...</p>
        <p className="text-xs mt-1 text-slate-600">Querying semantic overlays (IFC-LD, Brick, 223P)</p>
      </div>
    );
  }

  return (
    <div className="relative w-full h-full bg-nexus-800 rounded-lg overflow-hidden border border-nexus-600 shadow-inner">
      <div className="absolute top-2 left-3 z-10">
        <h3 className="text-xs font-mono text-nexus-accent uppercase tracking-widest">
          Semantic Knowledge Graph (RDF/IFC)
        </h3>
        <div className="flex gap-2 mt-1">
           <span className="flex items-center text-[10px] text-slate-400">
             <span className="w-2 h-2 rounded-full bg-nexus-accent mr-1"></span>Asset
           </span>
           <span className="flex items-center text-[10px] text-slate-400">
             <span className="w-2 h-2 rounded-full bg-nexus-success mr-1"></span>Sensor/Point
           </span>
           <span className="flex items-center text-[10px] text-slate-400">
             <span className="w-2 h-2 rounded-full bg-nexus-warning mr-1"></span>Warning
           </span>
        </div>
      </div>
      <ForceGraph2D
        graphData={graphData}
        nodeLabel={(node) => `${node.label || node.name || node.id.split('/').pop() || node.id}\n${node.type || ''}`}
        nodeColor={getNodeColor}
        nodeVal={getNodeSize}
        linkColor={() => '#475569'}
        linkOpacity={0.6}
        linkWidth={1.5}
        linkDirectionalArrowLength={6}
        linkDirectionalArrowRelPos={1}
        onNodeClick={handleNodeClick}
        backgroundColor="rgba(20, 20, 25, 0)"
        width={window.innerWidth - 600}
        height={window.innerHeight - 200}
      />
    </div>
  );
};

export default KnowledgeGraph;

