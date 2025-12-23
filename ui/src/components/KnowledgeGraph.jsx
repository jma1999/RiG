import React, { useCallback } from 'react';
import ForceGraph2D from 'react-force-graph-2d';

const KnowledgeGraph = ({ data, onNodeClick }) => {
  const handleNodeClick = useCallback((node) => {
    onNodeClick(node);
  }, [onNodeClick]);

  const getNodeColor = (node) => {
    if (node.status === 'warning') return '#ffb020';
    if (node.status === 'critical') return '#ff4d4d';
    if (node.type === 'Asset') return '#00f0ff';
    return '#00ff9d';
  };

  const getNodeSize = (node) => {
    if (node.type === 'Asset') return 12;
    return 8;
  };

  if (!data || !data.nodes || data.nodes.length === 0) {
    return (
      <div className="h-full w-full flex flex-col items-center justify-center text-slate-500 bg-nexus-800 rounded-lg border border-nexus-600">
        <p className="font-mono text-sm">No graph data available</p>
        <p className="text-xs mt-2 text-slate-600">Ask the agent to query the knowledge graph</p>
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
        graphData={data}
        nodeLabel={(node) => `${node.label || node.id}\n${node.type || ''}`}
        nodeColor={getNodeColor}
        nodeVal={getNodeSize}
        linkColor={() => '#475569'}
        linkOpacity={0.6}
        linkWidth={1.5}
        onNodeClick={handleNodeClick}
        backgroundColor="rgba(20, 20, 25, 0)"
        width={window.innerWidth - 600}
        height={window.innerHeight - 200}
      />
    </div>
  );
};

export default KnowledgeGraph;

