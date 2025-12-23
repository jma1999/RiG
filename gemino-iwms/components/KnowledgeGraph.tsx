import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import { GraphData, GraphNode, GraphLink } from '../types';

interface KnowledgeGraphProps {
  data: GraphData;
  onNodeClick: (node: GraphNode) => void;
  width?: number;
  height?: number;
}

const KnowledgeGraph: React.FC<KnowledgeGraphProps> = ({ data, onNodeClick, width = 600, height = 400 }) => {
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!svgRef.current || !data.nodes.length) return;

    // Clear previous render
    d3.select(svgRef.current).selectAll("*").remove();

    const svg = d3.select(svgRef.current)
      .attr("viewBox", [0, 0, width, height])
      .attr("style", "max-width: 100%; height: auto;");

    // Simulation setup
    const simulation = d3.forceSimulation(data.nodes as d3.SimulationNodeDatum[])
      .force("link", d3.forceLink(data.links).id((d: any) => d.id).distance(100))
      .force("charge", d3.forceManyBody().strength(-300))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collide", d3.forceCollide(40));

    // Arrow marker definition
    svg.append("defs").selectAll("marker")
      .data(["end"])
      .enter().append("marker")
      .attr("id", "arrow")
      .attr("viewBox", "0 -5 10 10")
      .attr("refX", 25) // Position of arrow relative to node
      .attr("refY", 0)
      .attr("markerWidth", 6)
      .attr("markerHeight", 6)
      .attr("orient", "auto")
      .append("path")
      .attr("d", "M0,-5L10,0L0,5")
      .attr("fill", "#64748b");

    // Draw links
    const link = svg.append("g")
      .attr("stroke", "#475569")
      .attr("stroke-opacity", 0.6)
      .selectAll("line")
      .data(data.links)
      .join("line")
      .attr("stroke-width", 1.5)
      .attr("marker-end", "url(#arrow)");

    // Draw nodes
    const node = svg.append("g")
      .attr("stroke", "#fff")
      .attr("stroke-width", 1.5)
      .selectAll("circle")
      .data(data.nodes)
      .join("circle")
      .attr("r", (d: any) => d.type === 'Asset' ? 12 : 8)
      .attr("fill", (d: any) => {
        switch (d.status) {
          case 'warning': return '#ffb020';
          case 'critical': return '#ff4d4d';
          default: return d.type === 'Asset' ? '#00f0ff' : '#00ff9d';
        }
      })
      .attr("cursor", "pointer")
      .call(drag(simulation) as any)
      .on("click", (event, d) => onNodeClick(d as unknown as GraphNode));

    // Labels
    const label = svg.append("g")
      .attr("class", "labels")
      .selectAll("text")
      .data(data.nodes)
      .join("text")
      .attr("dx", 15)
      .attr("dy", 4)
      .text((d: any) => d.label)
      .attr("fill", "#cbd5e1")
      .attr("font-size", "10px")
      .attr("font-family", "monospace");

    // Simulation tick
    simulation.on("tick", () => {
      link
        .attr("x1", (d: any) => d.source.x)
        .attr("y1", (d: any) => d.source.y)
        .attr("x2", (d: any) => d.target.x)
        .attr("y2", (d: any) => d.target.y);

      node
        .attr("cx", (d: any) => d.x)
        .attr("cy", (d: any) => d.y);

      label
        .attr("x", (d: any) => d.x)
        .attr("y", (d: any) => d.y);
    });

    // Cleanup
    return () => {
      simulation.stop();
    };
  }, [data, width, height, onNodeClick]);

  function drag(simulation: d3.Simulation<d3.SimulationNodeDatum, undefined>) {
    function dragstarted(event: any) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      event.subject.fx = event.subject.x;
      event.subject.fy = event.subject.y;
    }

    function dragged(event: any) {
      event.subject.fx = event.x;
      event.subject.fy = event.y;
    }

    function dragended(event: any) {
      if (!event.active) simulation.alphaTarget(0);
      event.subject.fx = null;
      event.subject.fy = null;
    }

    return d3.drag()
      .on("start", dragstarted)
      .on("drag", dragged)
      .on("end", dragended);
  }

  return (
    <div className="relative w-full h-full bg-nexus-800 rounded-lg overflow-hidden border border-nexus-600 shadow-inner">
      <div className="absolute top-2 left-3 z-10">
        <h3 className="text-xs font-mono text-nexus-accent uppercase tracking-widest">
          Semantic Knowledge Graph (RDF/IFC)
        </h3>
        <div className="flex gap-2 mt-1">
           <span className="flex items-center text-[10px] text-slate-400"><span className="w-2 h-2 rounded-full bg-nexus-accent mr-1"></span>Asset</span>
           <span className="flex items-center text-[10px] text-slate-400"><span className="w-2 h-2 rounded-full bg-nexus-success mr-1"></span>Sensor/Point</span>
           <span className="flex items-center text-[10px] text-slate-400"><span className="w-2 h-2 rounded-full bg-nexus-warning mr-1"></span>Warning</span>
        </div>
      </div>
      <svg ref={svgRef} className="w-full h-full opacity-90 hover:opacity-100 transition-opacity duration-300" />
    </div>
  );
};

export default KnowledgeGraph;