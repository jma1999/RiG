import React from 'react';
import { Activity } from 'lucide-react';

const TelemetryPanel = ({ data }) => {
  if (!data) {
    return (
      <div className="h-full w-full flex flex-col items-center justify-center text-slate-500 bg-nexus-800 rounded-lg border border-nexus-600">
        <Activity size={48} className="mb-4 opacity-20" />
        <p className="font-mono text-sm">No telemetry stream selected</p>
        <p className="text-xs mt-2 text-slate-600">Ask the agent to visualize data (e.g., "Show AHU-01 temp")</p>
      </div>
    );
  }

  const latestValue = data.data && data.data.length > 0 ? data.data[data.data.length - 1].value : 0;

  return (
    <div className="h-full w-full bg-nexus-800 rounded-lg border border-nexus-600 p-4 flex flex-col">
      <div className="flex justify-between items-center mb-4">
        <div>
          <h3 className="text-nexus-accent font-mono text-sm uppercase tracking-wider">{data.name}</h3>
          <p className="text-xs text-slate-400">Live Stream • TimescaleDB Aggregates</p>
        </div>
        <div className="text-right">
          <span className="text-2xl font-bold text-white">
            {latestValue.toFixed(1)}
          </span>
          <span className="text-sm text-slate-400 ml-1">{data.unit || ''}</span>
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
            {data.data && data.data.length > 1 && (
              <>
                <path
                  d={`M ${data.data.map((d, i) => `${(i / (data.data.length - 1)) * 800},${400 - (d.value / Math.max(...data.data.map(d => d.value))) * 350}`).join(' L ')}`}
                  fill="none"
                  stroke="#00f0ff"
                  strokeWidth="2"
                />
                <path
                  d={`M 0,400 L ${data.data.map((d, i) => `${(i / (data.data.length - 1)) * 800},${400 - (d.value / Math.max(...data.data.map(d => d.value))) * 350}`).join(' L ')} L 800,400 Z`}
                  fill="url(#gradient)"
                />
              </>
            )}
          </svg>
        </div>
      </div>
    </div>
  );
};

export default TelemetryPanel;

