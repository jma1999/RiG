import React, { useState, useEffect } from "react";
import { X, Grid, Plus, List, Calendar, Cloud, TrendingUp, MessageSquare, Bot } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { API_BASE } from "@/lib/env";

export default function RightSidebar({ selectedNode }) {
  const [aiInsights, setAiInsights] = useState({
    buildingCount: 82,
    occupancy: 1450,
    energyConsumption: 32.8,
    companyOwnedBuildings: 18,
    issues: 10,
    issuesChange: 3
  });
  const [aqi, setAqi] = useState({ value: 28, status: "Moderate", level: "moderate" });
  const [bhi, setBhi] = useState({ general: 91 });

  useEffect(() => {
    // Load real data from API if available
    const loadData = async () => {
      try {
        // Load telemetry data for AQI calculation
        const telemetryRes = await fetch(`${API_BASE}/telemetry/dashboard`);
        if (telemetryRes.ok) {
          const data = await telemetryRes.json();
          // Calculate AQI based on telemetry (mock for now)
          // In real implementation, this would use actual sensor data
        }

        // Load building health from agents
        // This would come from agent recommendations and telemetry analysis
      } catch (error) {
        console.warn("Failed to load sidebar data:", error);
      }
    };

    loadData();
    const interval = setInterval(loadData, 60000); // Update every minute
    return () => clearInterval(interval);
  }, []);

  const getAqiColor = (level) => {
    switch (level) {
      case "good": return "text-green-500";
      case "moderate": return "text-yellow-500";
      case "unhealthy": return "text-orange-500";
      default: return "text-[var(--palantir-text-muted)]";
    }
  };

  const getAqiBgColor = (level) => {
    switch (level) {
      case "good": return "bg-green-500";
      case "moderate": return "bg-yellow-500";
      case "unhealthy": return "bg-orange-500";
      default: return "bg-[var(--palantir-text-muted)]";
    }
  };

  return (
    <div className="w-80 bg-[var(--palantir-bg-secondary)] border-l border-[var(--palantir-border-primary)] h-full overflow-y-auto">
      {/* Header */}
      <div className="p-4 border-b border-[var(--palantir-border-primary)] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-[var(--palantir-text-primary)]">BMS</span>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
            <Grid className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
            <Plus className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
            <List className="h-4 w-4" />
          </Button>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-[var(--palantir-text-muted)]">Today</span>
          <Calendar className="h-4 w-4 text-[var(--palantir-text-muted)]" />
          <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
            <X className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <div className="p-4 space-y-4">
        {/* AI Insights Panel */}
        <Card className="bg-[var(--palantir-bg-elevated)] border-[var(--palantir-border-primary)]">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-semibold">AI insights</CardTitle>
              <Badge variant="outline" className="text-xs">2 min ago</Badge>
            </div>
            <Button variant="ghost" size="sm" className="text-xs h-6 mt-2 text-[var(--palantir-text-accent)]">
              Chat with AI &gt;
            </Button>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-xs text-[var(--palantir-text-muted)] leading-relaxed">
              The Building Management System (BMS) allows users to control various building components and monitor building-related data in real time. It provides insights into building performance and offers control over elements like ventilation, door access, and more.
            </p>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div>
                <div className="text-[var(--palantir-text-muted)]">Building Count</div>
                <div className="text-lg font-semibold text-[var(--palantir-text-primary)]">{aiInsights.buildingCount}</div>
              </div>
              <div>
                <div className="text-[var(--palantir-text-muted)]">Occupancy</div>
                <div className="text-lg font-semibold text-[var(--palantir-text-primary)]">{aiInsights.occupancy.toLocaleString()}</div>
              </div>
              <div>
                <div className="text-[var(--palantir-text-muted)]">Energy Consumption</div>
                <div className="text-lg font-semibold text-[var(--palantir-text-primary)]">{aiInsights.energyConsumption} kWh</div>
              </div>
              <div>
                <div className="text-[var(--palantir-text-muted)]">Company-Owned Buildings</div>
                <div className="text-lg font-semibold text-[var(--palantir-text-primary)]">{aiInsights.companyOwnedBuildings}</div>
              </div>
              <div className="col-span-2">
                <div className="flex items-center justify-between">
                  <div className="text-[var(--palantir-text-muted)]">Issues</div>
                  <div className="flex items-center gap-1">
                    <div className="text-lg font-semibold text-[var(--palantir-text-primary)]">{aiInsights.issues}</div>
                    <Badge variant="outline" className="text-xs bg-red-500/20 text-red-500 border-red-500">
                      +{aiInsights.issuesChange}%
                    </Badge>
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Air Quality Index Panel */}
        <Card className="bg-[var(--palantir-bg-elevated)] border-[var(--palantir-border-primary)]">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-semibold">Air Quality Index (AQI)</CardTitle>
              <div className="flex items-center gap-1">
                <span className="text-xs text-[var(--palantir-text-muted)]">Today</span>
                <Calendar className="h-3 w-3 text-[var(--palantir-text-muted)]" />
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {/* Circular Gauge (simplified as progress bar) */}
            <div className="flex items-center justify-center">
              <div className="relative w-32 h-32">
                <svg className="transform -rotate-90 w-32 h-32">
                  <circle
                    cx="64"
                    cy="64"
                    r="56"
                    stroke="var(--palantir-bg-tertiary)"
                    strokeWidth="8"
                    fill="none"
                  />
                  <circle
                    cx="64"
                    cy="64"
                    r="56"
                    stroke={getAqiBgColor(aqi.level)}
                    strokeWidth="8"
                    fill="none"
                    strokeDasharray={`${(aqi.value / 100) * 352} 352`}
                    strokeLinecap="round"
                  />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <Cloud className={`h-8 w-8 ${getAqiColor(aqi.level)}`} />
                  <div className={`text-2xl font-bold ${getAqiColor(aqi.level)}`}>{aqi.value}%</div>
                  <div className={`text-xs ${getAqiColor(aqi.level)}`}>{aqi.status}</div>
                </div>
              </div>
            </div>

            {/* AQI Legend */}
            <div className="space-y-1 text-xs">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-green-500"></div>
                  <span className="text-[var(--palantir-text-muted)]">0-25 Good</span>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
                  <span className="text-[var(--palantir-text-muted)]">26-50 Moderate</span>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-orange-500"></div>
                  <span className="text-[var(--palantir-text-muted)]">51-100 Unhealthy</span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Building Health Index Panel */}
        <Card className="bg-[var(--palantir-bg-elevated)] border-[var(--palantir-border-primary)]">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-semibold">Building Health Index (BHI)</CardTitle>
              <div className="flex items-center gap-1">
                <span className="text-xs text-[var(--palantir-text-muted)]">Today</span>
                <Calendar className="h-3 w-3 text-[var(--palantir-text-muted)]" />
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-[var(--palantir-text-primary)]">General BHI</span>
                <span className="text-lg font-semibold text-[var(--palantir-success)]">{bhi.general}%</span>
              </div>
              <Progress value={bhi.general} className="h-2" />
            </div>

            {/* Node-specific info if selected */}
            {selectedNode && (
              <div className="mt-4 pt-4 border-t border-[var(--palantir-border-primary)]">
                <div className="text-xs text-[var(--palantir-text-muted)] mb-2">Selected Node</div>
                <div className="text-sm font-medium text-[var(--palantir-text-primary)]">{selectedNode.name}</div>
                <div className="text-xs text-[var(--palantir-text-muted)] mt-1">{selectedNode.type}</div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

