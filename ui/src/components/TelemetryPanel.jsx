import React, { useState, useEffect } from 'react';
import { Activity } from 'lucide-react';
import { API_BASE } from "@/lib/env";

const TelemetryPanel = ({ data }) => {
  const [telemetryPoints, setTelemetryPoints] = useState([]);
  const [selectedPoint, setSelectedPoint] = useState(null);

  useEffect(() => {
    if (data) {
      setSelectedPoint(data);
    } else {
      // Load available telemetry points
      loadTelemetryPoints();
    }
  }, [data]);

  const loadTelemetryPoints = async () => {
    try {
      const res = await fetch(`${API_BASE}/telemetry/points`);
      if (res.ok) {
        const result = await res.json();
        setTelemetryPoints(result.points || []);
      }
    } catch (error) {
      console.error("Failed to load telemetry points:", error);
    }
  };

  if (!selectedPoint && !data) {
    return (
      <div className="h-full w-full flex flex-col items-center justify-center text-slate-500 bg-nexus-800 rounded-lg border border-nexus-600 p-6">
        <Activity size={48} className="mb-4 opacity-20" />
        <p className="font-mono text-sm">No telemetry stream selected</p>
        <p className="text-xs mt-2 text-slate-600">Ask the agent to visualize data (e.g., "Show ft_136276_sat")</p>
        {telemetryPoints.length > 0 && (
          <div className="mt-4 text-xs text-slate-500">
            Available points: {telemetryPoints.map(p => p.point_id).join(', ')}
          </div>
        )}
      </div>
    );
  }

  const displayData = selectedPoint || data;
  const latestValue = displayData?.data && displayData.data.length > 0 
    ? displayData.data[displayData.data.length - 1].value 
    : 0;

  const chartData = displayData?.data || [];
  const maxValue = chartData.length > 0 ? Math.max(...chartData.map(d => d.value)) : 1;
  const minValue = chartData.length > 0 ? Math.min(...chartData.map(d => d.value)) : 0;
  const range = maxValue - minValue || 1;

  return (
    <div className="h-full w-full bg-nexus-800 rounded-lg border border-nexus-600 p-4 flex flex-col">
      <div className="flex justify-between items-center mb-4">
        <div>
          <h3 className="text-nexus-accent font-mono text-sm uppercase tracking-wider">
            {displayData.name || displayData.id}
          </h3>
          <p className="text-xs text-slate-400">Live Stream • TimescaleDB Aggregates</p>
        </div>
        <div className="text-right">
          <span className="text-2xl font-bold text-white">
            {latestValue.toFixed(1)}
          </span>
          <span className="text-sm text-slate-400 ml-1">{displayData.unit || ''}</span>
        </div>
      </div>
      
      <div className="flex-grow min-h-0 flex items-center justify-center">
        <div className="w-full h-full relative">
          {/* Simple line chart visualization */}
          <svg className="w-full h-full" viewBox="0 0 800 400" preserveAspectRatio="none">
            <defs>
              <linearGradient id="gradient" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="5%" stopColor="#00f0ff" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#00f0ff" stopOpacity={0}/>
              </linearGradient>
            </defs>
            {/* Grid lines */}
            {[0, 1, 2, 3, 4].map(i => (
              <line
                key={i}
                x1="0"
                y1={i * 100}
                x2="800"
                y2={i * 100}
                stroke="#2d2d3a"
                strokeWidth="1"
                strokeDasharray="3 3"
              />
            ))}
            {/* Data line */}
            {chartData.length > 1 && (
              <>
                <path
                  d={`M ${chartData.map((d, i) => `${(i / (chartData.length - 1)) * 800},${400 - ((d.value - minValue) / range) * 350}`).join(' L ')}`}
                  fill="none"
                  stroke="#00f0ff"
                  strokeWidth="2"
                />
                <path
                  d={`M 0,400 L ${chartData.map((d, i) => `${(i / (chartData.length - 1)) * 800},${400 - ((d.value - minValue) / range) * 350}`).join(' L ')} L 800,400 Z`}
                  fill="url(#gradient)"
                />
              </>
            )}
            {chartData.length === 0 && (
              <text x="400" y="200" textAnchor="middle" fill="#64748b" fontSize="14">
                No data points available
              </text>
            )}
          </svg>
        </div>
      </div>
    </div>
  );
};

export default TelemetryPanel;

