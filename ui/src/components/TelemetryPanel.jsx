import React, { useState, useEffect } from 'react';
import { Activity, RefreshCw } from 'lucide-react';
import { API_BASE } from "@/lib/env";

const TelemetryPanel = ({ data }) => {
  const [telemetryPoints, setTelemetryPoints] = useState([]);
  const [selectedPoint, setSelectedPoint] = useState(data);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (data) {
      setSelectedPoint(data);
    } else {
      // Load available telemetry points on mount
      loadTelemetryPoints();
    }
  }, [data]);

  const loadTelemetryPoints = async () => {
    setLoading(true);
    try {
      console.log("Loading telemetry points from TimescaleDB...");
      const res = await fetch(`${API_BASE}/telemetry/points`);
      if (res.ok) {
        const result = await res.json();
        const points = result.points || [];
        setTelemetryPoints(points);
        console.log(`✅ Loaded ${points.length} telemetry points from TimescaleDB`);
        
        // Auto-select first point if available and no data is selected
        if (points.length > 0 && !selectedPoint) {
          const firstPoint = points[0];
          await loadPointData(firstPoint.point_id);
        }
      } else {
        const errorText = await res.text();
        console.error("Failed to load telemetry points:", res.status, errorText);
      }
    } catch (error) {
      console.error("Failed to load telemetry points:", error);
    } finally {
      setLoading(false);
    }
  };

  const loadPointData = async (pointId) => {
    setLoading(true);
    try {
      console.log(`Loading data for point: ${pointId}`);
      
      // First seed data to ensure we have data
      await fetch(`${API_BASE}/telemetry/seed/${pointId}?count=60`, { method: "POST" });
      
      // Wait for data to commit
      await new Promise(resolve => setTimeout(resolve, 500));
      
      // Then fetch the data
      const res = await fetch(`${API_BASE}/telemetry/points/${pointId}?hours=24&limit=100`);
      if (res.ok) {
        const data = await res.json();
        const telemetry = {
          id: pointId,
          name: `${pointId}`,
          unit: data.unit || '°C',
          data: (data.data || []).map(d => ({
            timestamp: new Date(d.time || d.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            value: parseFloat(d.value) || 0
          }))
        };
        setSelectedPoint(telemetry);
        console.log(`✅ Loaded ${telemetry.data.length} data points for ${pointId}`);
      }
    } catch (error) {
      console.error("Failed to load point data:", error);
    } finally {
      setLoading(false);
    }
  };

  if (!selectedPoint && !data) {
    return (
      <div className="h-full w-full flex flex-col bg-nexus-800 rounded-lg border border-nexus-600 p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-nexus-accent font-mono text-sm uppercase tracking-wider">Available Telemetry Points</h3>
          <button
            onClick={loadTelemetryPoints}
            disabled={loading}
            className="p-2 hover:bg-nexus-700 rounded-lg transition-colors text-slate-400"
          >
            <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
          </button>
        </div>
        
        {loading ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-nexus-accent mx-auto mb-2"></div>
              <p className="text-sm text-slate-400">Loading from TimescaleDB...</p>
            </div>
          </div>
        ) : telemetryPoints.length > 0 ? (
          <div className="space-y-2 overflow-y-auto">
            {telemetryPoints.map((point) => (
              <button
                key={point.point_id}
                onClick={() => loadPointData(point.point_id)}
                className="w-full text-left p-3 bg-nexus-900/50 border border-nexus-700 rounded-lg hover:border-nexus-accent/50 hover:bg-nexus-900 transition-all"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-white">{point.point_id}</p>
                    <p className="text-xs text-slate-400">
                      {point.data_points || 0} readings • Last: {point.last_reading ? new Date(point.last_reading).toLocaleString() : 'N/A'}
                    </p>
                  </div>
                  <Activity size={16} className="text-nexus-accent" />
                </div>
              </button>
            ))}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-slate-500">
            <Activity size={48} className="mb-4 opacity-20" />
            <p className="font-mono text-sm">No telemetry points found</p>
            <p className="text-xs mt-2 text-slate-600">Ask the agent to visualize data or check TimescaleDB connection</p>
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

