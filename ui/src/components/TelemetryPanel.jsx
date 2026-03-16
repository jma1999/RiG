import React, { useState, useEffect } from 'react';
import { Activity, RefreshCw } from 'lucide-react';
import { API_BASE } from "@/lib/env";

const TelemetryPanel = ({ data, graphSensors = [] }) => {
  const [telemetryPoints, setTelemetryPoints] = useState([]);
  const [selectedPoint, setSelectedPoint] = useState(data);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (data) {
      setSelectedPoint(data);
    } else {
      loadTelemetryPoints();
    }
  }, [data]);

  useEffect(() => {
    if (graphSensors.length > 0 && telemetryPoints.length === 0) {
      setTelemetryPoints(graphSensors);
    }
  }, [graphSensors]);

  const loadTelemetryPoints = async () => {
    setLoading(true);
    try {
      const gsRes = await fetch(`${API_BASE}/telemetry/graph-sensors`);
      if (gsRes.ok) {
        const gsData = await gsRes.json();
        const sensors = gsData.sensors || [];
        if (sensors.length > 0) {
          setTelemetryPoints(sensors);
          console.log(`Loaded ${sensors.length} sensors from graph-sensors endpoint`);
          setLoading(false);
          return;
        }
      }

      const res = await fetch(`${API_BASE}/telemetry/points`);
      if (res.ok) {
        const result = await res.json();
        const points = result.points || [];
        setTelemetryPoints(points);
        console.log(`Loaded ${points.length} telemetry points from TimescaleDB`);
        
        if (points.length > 0 && !selectedPoint) {
          const firstPoint = points[0];
          await loadPointData(firstPoint.point_id);
        }
      }
    } catch (error) {
      console.error("Failed to load telemetry points:", error);
    } finally {
      setLoading(false);
    }
  };

  const loadPointData = async (pointId) => {
    setLoading(true);
    const sensorInfo = telemetryPoints.find(p => p.point_id === pointId);
    try {
      console.log(`Loading data for point: ${pointId}`);

      const res = await fetch(`${API_BASE}/telemetry/points/${pointId}?hours=24&limit=200`);
      if (res.ok) {
        const data = await res.json();
        const rows = (data.data || []).map(d => ({
          timestamp: new Date(d.time || d.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          value: parseFloat(d.value) || 0,
        }));

        setSelectedPoint({
          id: pointId,
          name: sensorInfo?.label || pointId,
          unit: data.unit || sensorInfo?.unit || '',
          data: rows,
          latestValue: sensorInfo?.latest_value,
          sensorType: sensorInfo?.sensor_type,
          quantityKind: sensorInfo?.quantity_kind,
          source: sensorInfo?.source || 'timescaledb',
        });
        console.log(`Loaded ${rows.length} data points for ${pointId}`);
      } else {
        setSelectedPoint({
          id: pointId,
          name: sensorInfo?.label || pointId,
          unit: sensorInfo?.unit || '',
          data: [],
          latestValue: sensorInfo?.latest_value,
          sensorType: sensorInfo?.sensor_type,
          quantityKind: sensorInfo?.quantity_kind,
          source: sensorInfo?.source || 'timescaledb',
        });
      }
    } catch (error) {
      console.error("Failed to load point data:", error);
      setSelectedPoint({
        id: pointId,
        name: sensorInfo?.label || pointId,
        unit: sensorInfo?.unit || '',
        data: [],
        latestValue: sensorInfo?.latest_value,
        sensorType: sensorInfo?.sensor_type,
        quantityKind: sensorInfo?.quantity_kind,
        source: sensorInfo?.source || 'timescaledb',
      });
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
            {telemetryPoints.map((point) => {
              const isLive = point.status === 'LIVE';
              return (
                <button
                  key={point.point_id}
                  onClick={() => loadPointData(point.point_id)}
                  className="w-full text-left p-3 bg-nexus-900/50 border border-nexus-700 rounded-lg transition-all hover:border-nexus-accent/50 hover:bg-nexus-900 cursor-pointer"
                >
                  <div className="flex items-center justify-between">
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-white truncate">{point.label || point.point_id}</p>
                      <p className="text-xs text-slate-400 truncate">
                        {point.sensor_type || point.quantity_kind || 'Sensor'}
                        {point.data_points ? ` · ${point.data_points} readings` : ''}
                        {point.last_reading ? ` · ${new Date(point.last_reading).toLocaleString()}` : ''}
                      </p>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      {point.latest_value != null && (
                        <span className="text-sm font-mono text-white">
                          {typeof point.latest_value === 'number' ? point.latest_value.toFixed(1) : point.latest_value}
                          {point.unit ? <span className="text-[10px] text-slate-500 ml-0.5">{point.unit}</span> : null}
                        </span>
                      )}
                      <span className={`px-2 py-0.5 rounded text-[10px] font-mono ${
                        isLive ? 'bg-green-900/50 text-green-400' : 'bg-amber-900/50 text-amber-400'
                      }`}>
                        {isLive ? 'LIVE' : 'NO DATA'}
                      </span>
                    </div>
                  </div>
                </button>
              );
            })}
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
  const chartData = displayData?.data || [];
  const latestValue = chartData.length > 0
  ? chartData[chartData.length - 1].value
  : (displayData?.latestValue != null ? displayData.latestValue : null);

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
          <p className="text-xs text-slate-400">
            {chartData.length > 0
              ? `Time-series • ${displayData.source || 'timescaledb'}`
              : (displayData.quantityKind || displayData.sensorType || 'Sensor')}
          </p>
          <button
            onClick={() => { setSelectedPoint(null); }}
            className="text-[10px] text-slate-500 hover:text-nexus-accent mt-1 transition-colors"
          >
            ← Back to sensor list
          </button>
        </div>
        <div className="text-right">
          {latestValue != null ? (
            <>
              <span className="text-2xl font-bold text-white">
                {typeof latestValue === 'number' ? latestValue.toFixed(1) : latestValue}
              </span>
              <span className="text-sm text-slate-400 ml-1">{displayData.unit || displayData.dtUnit || ''}</span>
            </>
          ) : (
            <span className="text-sm text-slate-500">No readings</span>
          )}
        </div>
      </div>
      
      <div className="flex-grow min-h-0 flex items-center justify-center">
        {chartData.length > 0 ? (
          <div className="w-full h-full relative">
            <svg className="w-full h-full" viewBox="0 0 800 400" preserveAspectRatio="none">
              <defs>
                <linearGradient id="gradient" x1="0%" y1="0%" x2="0%" y2="100%">
                  <stop offset="5%" stopColor="#00f0ff" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#00f0ff" stopOpacity={0}/>
                </linearGradient>
              </defs>
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
            </svg>
          </div>
        ) : (
          <div className="text-center text-slate-500 space-y-2">
            <Activity size={36} className="mx-auto opacity-30" />
            <p className="text-sm">No time-series data in TimescaleDB yet</p>
            {displayData?.latestValue != null && (
              <p className="text-xs text-nexus-accent/70">
                Latest available reading: {displayData.latestValue} {displayData.unit || ''}
              </p>
            )}
            <p className="text-xs text-slate-600">
              No historical series returned from TimescaleDB for this point yet
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default TelemetryPanel;

