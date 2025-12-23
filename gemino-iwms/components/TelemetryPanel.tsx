import React from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { TelemetrySeries } from '../types';
import { Activity } from 'lucide-react';

interface TelemetryPanelProps {
  data: TelemetrySeries | null;
}

const TelemetryPanel: React.FC<TelemetryPanelProps> = ({ data }) => {
  if (!data) {
    return (
      <div className="h-full w-full flex flex-col items-center justify-center text-slate-500 bg-nexus-800 rounded-lg border border-nexus-600">
        <Activity size={48} className="mb-4 opacity-20" />
        <p className="font-mono text-sm">No telemetry stream selected</p>
        <p className="text-xs mt-2 text-slate-600">Ask the agent to visualize data (e.g., "Show AHU-01 temp")</p>
      </div>
    );
  }

  return (
    <div className="h-full w-full bg-nexus-800 rounded-lg border border-nexus-600 p-4 flex flex-col">
      <div className="flex justify-between items-center mb-4">
        <div>
          <h3 className="text-nexus-accent font-mono text-sm uppercase tracking-wider">{data.name}</h3>
          <p className="text-xs text-slate-400">Live Stream • Cloud Storage Aggregates</p>
        </div>
        <div className="text-right">
          <span className="text-2xl font-bold text-white">
            {data.data[data.data.length - 1].value}
          </span>
          <span className="text-sm text-slate-400 ml-1">{data.unit}</span>
        </div>
      </div>
      
      <div className="flex-grow min-h-0">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data.data}>
            <defs>
              <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#00f0ff" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#00f0ff" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#2d2d3a" vertical={false} />
            <XAxis 
              dataKey="timestamp" 
              tick={{fill: '#64748b', fontSize: 10}} 
              stroke="#2d2d3a" 
            />
            <YAxis 
              tick={{fill: '#64748b', fontSize: 10}} 
              stroke="#2d2d3a"
              domain={['auto', 'auto']}
            />
            <Tooltip 
              contentStyle={{backgroundColor: '#141419', borderColor: '#2d2d3a', color: '#e2e8f0'}}
              itemStyle={{color: '#00f0ff'}}
            />
            <Area 
              type="monotone" 
              dataKey="value" 
              stroke="#00f0ff" 
              strokeWidth={2}
              fillOpacity={1} 
              fill="url(#colorValue)" 
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default TelemetryPanel;