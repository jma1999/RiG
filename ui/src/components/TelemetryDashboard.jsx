import React, { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogClose } from "@/components/ui/dialog";
import { API_BASE } from "@/lib/env";
import { Activity, TrendingUp, Thermometer, Gauge } from "lucide-react";

// Map sensor IDs to human-readable names
const getSensorDisplayName = (pointId) => {
  const nameMap = {
    "ft_136276_sat": "Supply Air Temperature",
    "ft_136276_saf": "Supply Air Flow",
    "ft_136276_damper_position": "Damper Position",
    "ft_136276_damper_command": "Damper Command",
    "ft_136276_run_status": "Run Status",
  };
  
  const readableName = nameMap[pointId] || pointId.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase());
  return `${readableName} (${pointId})`;
};

export default function TelemetryDashboard() {
  const [telemetryPoints, setTelemetryPoints] = useState([]);
  const [selectedPoint, setSelectedPoint] = useState(null);
  const [telemetryData, setTelemetryData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showReadingsModal, setShowReadingsModal] = useState(false);
  const [modalPointId, setModalPointId] = useState(null);
  const [modalReadings, setModalReadings] = useState([]);

  useEffect(() => {
    loadTelemetryPoints();
  }, []);

  useEffect(() => {
    if (selectedPoint) {
      loadTelemetryData(selectedPoint);
      const interval = setInterval(() => {
        loadTelemetryData(selectedPoint);
      }, 5000); // Refresh every 5 seconds
      return () => clearInterval(interval);
    }
  }, [selectedPoint]);

  const loadTelemetryPoints = async () => {
    try {
      const res = await fetch(`${API_BASE}/telemetry/points`);
      if (res.ok) {
        const data = await res.json();
        setTelemetryPoints(data.points || []);
        if (data.points && data.points.length > 0) {
          setSelectedPoint(data.points[0].point_id);
        }
      }
    } catch (error) {
      console.error("Failed to load telemetry points:", error);
    } finally {
      setLoading(false);
    }
  };

  const loadTelemetryData = async (pointId) => {
    try {
      const res = await fetch(`${API_BASE}/telemetry/points/${pointId}?hours=1&limit=60`);
      if (res.ok) {
        const data = await res.json();
        setTelemetryData(data.data || []);
      }
    } catch (error) {
      console.error("Failed to load telemetry data:", error);
    }
  };

  const getLatestValue = () => {
    if (telemetryData.length === 0) return null;
    return telemetryData[telemetryData.length - 1];
  };

  const getMinMax = () => {
    if (telemetryData.length === 0) return { min: 0, max: 0 };
    const values = telemetryData.map(d => d.value);
    return {
      min: Math.min(...values),
      max: Math.max(...values),
      avg: values.reduce((a, b) => a + b, 0) / values.length
    };
  };

  const latest = getLatestValue();
  const stats = getMinMax();

  const handlePointClick = async (pointId) => {
    setModalPointId(pointId);
    setShowReadingsModal(true);
    // Load readings for the clicked point
    try {
      const res = await fetch(`${API_BASE}/telemetry/points/${pointId}?hours=1&limit=60`);
      if (res.ok) {
        const data = await res.json();
        setModalReadings(data.data || []);
      }
    } catch (error) {
      console.error("Failed to load modal readings:", error);
      setModalReadings([]);
    }
  };

  return (
    <div className="flex-1 p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-[var(--palantir-text-primary)]">
            Live Telemetry Dashboard
          </h1>
          <p className="text-[var(--palantir-text-secondary)] mt-2">
            Real-time sensor data from TimescaleDB, semantically linked to GraphDB
          </p>
        </div>
        <Badge className="bg-green-600 text-white">
          <Activity className="h-3 w-3 mr-1" />
          Live Data
        </Badge>
      </div>

      {/* Telemetry Points List */}
      {loading ? (
        <div className="flex items-center justify-center p-12">
          <div className="text-center space-y-2">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[var(--palantir-text-accent)] mx-auto"></div>
            <p className="text-sm text-[var(--palantir-text-muted)]">Loading telemetry points...</p>
          </div>
        </div>
      ) : telemetryPoints.length === 0 ? (
        <Card className="palantir-card">
          <CardContent className="p-6 text-center space-y-4">
            <p className="text-[var(--palantir-text-muted)]">
              No telemetry points found. Loading mock data for demonstration...
            </p>
            <Button
              onClick={() => {
                // Force reload with mock data
                setTelemetryPoints([
                  {
                    point_id: "ft_136276_sat",
                    data_points: 60,
                    first_reading: new Date(Date.now() - 3600000).toISOString(),
                    last_reading: new Date().toISOString()
                  }
                ]);
                setSelectedPoint("ft_136276_sat");
              }}
              variant="outline"
            >
              Load Demo Data
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {telemetryPoints.map((point) => (
          <Card
            key={point.point_id}
            className={`palantir-card cursor-pointer transition-all ${
              selectedPoint === point.point_id
                ? "ring-2 ring-[var(--palantir-text-accent)]"
                : ""
            }`}
            onClick={() => {
              setSelectedPoint(point.point_id);
              handlePointClick(point.point_id);
            }}
          >
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <p className="text-sm font-semibold text-[var(--palantir-text-primary)]">
                    {getSensorDisplayName(point.point_id)}
                  </p>
                  <p className="text-xs text-[var(--palantir-text-muted)] mt-1">
                    {point.data_points} readings • Click to view all
                  </p>
                </div>
                <Thermometer className="h-8 w-8 text-[var(--palantir-text-accent)] ml-2" />
              </div>
            </CardContent>
          </Card>
          ))}
        </div>
      )}

      {/* Selected Point Details */}
      {selectedPoint && latest && telemetryData.length > 0 && (
        <>
          <div className="grid grid-cols-4 gap-6">
            <Card className="palantir-card">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-[var(--palantir-text-muted)]">Current Value</p>
                    <p className="text-3xl font-bold text-[var(--palantir-text-primary)]">
                      {latest.value.toFixed(2)}
                    </p>
                    <p className="text-xs text-[var(--palantir-text-muted)] mt-1">
                      {latest.quality}
                    </p>
                  </div>
                  <Gauge className="h-8 w-8 text-[var(--palantir-text-accent)]" />
                </div>
              </CardContent>
            </Card>

            <Card className="palantir-card">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-[var(--palantir-text-muted)]">Minimum</p>
                    <p className="text-2xl font-bold text-[var(--palantir-text-primary)]">
                      {stats.min.toFixed(2)}
                    </p>
                  </div>
                  <TrendingUp className="h-8 w-8 text-blue-500" />
                </div>
              </CardContent>
            </Card>

            <Card className="palantir-card">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-[var(--palantir-text-muted)]">Maximum</p>
                    <p className="text-2xl font-bold text-[var(--palantir-text-primary)]">
                      {stats.max.toFixed(2)}
                    </p>
                  </div>
                  <TrendingUp className="h-8 w-8 text-red-500" />
                </div>
              </CardContent>
            </Card>

            <Card className="palantir-card">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-[var(--palantir-text-muted)]">Average</p>
                    <p className="text-2xl font-bold text-[var(--palantir-text-primary)]">
                      {stats.avg.toFixed(2)}
                    </p>
                  </div>
                  <Activity className="h-8 w-8 text-[var(--palantir-text-accent)]" />
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Time Series Chart */}
          <Card className="palantir-card-elevated">
            <CardHeader>
              <CardTitle>Time Series Data (Last Hour)</CardTitle>
              <p className="text-sm text-[var(--palantir-text-muted)]">
                {getSensorDisplayName(selectedPoint)} | Linked via semantic overlay (223P/Brick/QUDT)
              </p>
            </CardHeader>
            <CardContent>
              <div className="h-64 flex items-end justify-between gap-1">
                {telemetryData.map((point, index) => {
                  const height = ((point.value - stats.min) / (stats.max - stats.min || 1)) * 100;
                  return (
                    <div
                      key={index}
                      className="flex-1 bg-[var(--palantir-text-accent)] rounded-t transition-all hover:opacity-80"
                      style={{ height: `${Math.max(height, 5)}%` }}
                      title={`${point.value.toFixed(2)} at ${new Date(point.timestamp).toLocaleTimeString()}`}
                    />
                  );
                })}
              </div>
              <div className="mt-4 flex justify-between text-xs text-[var(--palantir-text-muted)]">
                <span>{telemetryData[0]?.timestamp ? new Date(telemetryData[0].timestamp).toLocaleTimeString() : ""}</span>
                <span>{latest.timestamp ? new Date(latest.timestamp).toLocaleTimeString() : ""}</span>
              </div>
            </CardContent>
          </Card>
        </>
      )}

      {/* Readings Modal */}
      <Dialog open={showReadingsModal} onOpenChange={setShowReadingsModal}>
        <DialogContent>
          <DialogHeader>
            <div className="flex items-center justify-between">
              <DialogTitle>
                {modalPointId ? getSensorDisplayName(modalPointId) : "Sensor Readings"}
              </DialogTitle>
              <DialogClose onClose={() => setShowReadingsModal(false)} />
            </div>
          </DialogHeader>
          
          <div className="mt-4">
            {modalPointId && (
              <div className="space-y-4">
                <div className="flex items-center justify-between text-sm text-[var(--palantir-text-muted)] mb-4">
                  <span>Showing all {modalReadings.length} readings from the last hour</span>
                  <Badge variant="outline">{modalReadings.length} total</Badge>
                </div>
                
                <div className="border border-[var(--palantir-border-primary)] rounded-lg overflow-hidden">
                  <div className="max-h-[60vh] overflow-y-auto">
                    <table className="w-full text-sm">
                      <thead className="bg-[var(--palantir-bg-secondary)] sticky top-0">
                        <tr>
                          <th className="px-4 py-3 text-left font-semibold text-[var(--palantir-text-primary)] border-b border-[var(--palantir-border-primary)]">
                            #
                          </th>
                          <th className="px-4 py-3 text-left font-semibold text-[var(--palantir-text-primary)] border-b border-[var(--palantir-border-primary)]">
                            Timestamp
                          </th>
                          <th className="px-4 py-3 text-left font-semibold text-[var(--palantir-text-primary)] border-b border-[var(--palantir-border-primary)]">
                            Value
                          </th>
                          <th className="px-4 py-3 text-left font-semibold text-[var(--palantir-text-primary)] border-b border-[var(--palantir-border-primary)]">
                            Quality
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {modalReadings.map((reading, index) => (
                          <tr
                            key={index}
                            className="border-b border-[var(--palantir-border-primary)] hover:bg-[var(--palantir-bg-secondary)] transition-colors"
                          >
                            <td className="px-4 py-3 text-[var(--palantir-text-muted)] font-mono">
                              {index + 1}
                            </td>
                            <td className="px-4 py-3 text-[var(--palantir-text-primary)]">
                              {new Date(reading.timestamp).toLocaleString()}
                            </td>
                            <td className="px-4 py-3 text-[var(--palantir-text-primary)] font-semibold">
                              {reading.value.toFixed(2)}
                            </td>
                            <td className="px-4 py-3">
                              <Badge
                                variant={reading.quality === "GOOD" ? "default" : "outline"}
                                className={
                                  reading.quality === "GOOD"
                                    ? "bg-green-600 text-white"
                                    : ""
                                }
                              >
                                {reading.quality}
                              </Badge>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
                
                {modalReadings.length === 0 && (
                  <div className="text-center py-8 text-[var(--palantir-text-muted)]">
                    No readings available for this sensor.
                  </div>
                )}
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

