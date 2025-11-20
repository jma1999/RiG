import React, { useState } from "react";
import { Search, Filter, Plus, Star, Edit, Trash2, ChevronUp, ChevronDown, Radar, Eye, Wind, AlertTriangle, Network, Layers, Settings } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export default function LeftSidebar({ activeTab, onTabChange, selectedBuilding, onBuildingSelect }) {
  const [activeLeftTab, setActiveLeftTab] = useState("functions");
  const [buildingsExpanded, setBuildingsExpanded] = useState(true);
  const [buildings] = useState([
    { id: "bldg-001", name: "Technique Building", location: "Central Zone", icon: "🏢" },
    { id: "bldg-002", name: "Logistics Center", location: "North Zone", icon: "🏭" },
    { id: "bldg-003", name: "Sub Central building", location: "Central Zone", icon: "🏛️" },
    { id: "bldg-004", name: "Commercial Building", location: "South Zone", icon: "🏬" },
    { id: "bldg-005", name: "Technique building", location: "East Zone", icon: "🏢" },
    { id: "bldg-006", name: "Logistics Center", location: "West Zone", icon: "🏭" }
  ]);
  const [searchQuery, setSearchQuery] = useState("");

  const leftTabs = [
    { id: "classes", label: "Classes", icon: Layers },
    { id: "outliners", label: "Outliners", icon: Eye },
    { id: "functions", label: "Functions", icon: Settings }
  ];

  const functions = [
    { id: "radar", name: "Radar", icon: Radar },
    { id: "surveillance", name: "Surveillance", icon: Eye },
    { id: "aq", name: "AQ", icon: Wind },
    { id: "traffic", name: "Traffic Management", icon: Network },
    { id: "emergency", name: "Emergency Coordination", icon: AlertTriangle },
    { id: "bms", name: "BMS", icon: Settings, active: true },
    { id: "simulation", name: "Simulation", icon: Layers },
    { id: "custom", name: "Custom functions", icon: Settings },
    { id: "layers", name: "Layers", icon: Layers }
  ];

  const filteredBuildings = buildings.filter(b => 
    b.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    b.location.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="w-64 bg-[var(--palantir-bg-secondary)] border-r border-[var(--palantir-border-primary)] h-full flex flex-col">
      {/* Top Section - Tabs */}
      <div className="p-4 border-b border-[var(--palantir-border-primary)]">
        <div className="flex gap-2 mb-4">
          {leftTabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveLeftTab(tab.id)}
                className={cn(
                  "flex-1 px-3 py-2 rounded-lg text-xs font-medium transition-colors",
                  activeLeftTab === tab.id
                    ? "bg-[var(--palantir-text-accent)] text-black"
                    : "bg-[var(--palantir-bg-tertiary)] text-[var(--palantir-text-primary)] hover:bg-[var(--palantir-hover)]"
                )}
              >
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-[var(--palantir-text-muted)]" />
          <Input
            placeholder="Q Search"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9 pr-9 h-8 text-xs bg-[var(--palantir-bg-tertiary)] border-[var(--palantir-border-primary)]"
          />
          <Filter className="absolute right-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-[var(--palantir-text-muted)]" />
        </div>
      </div>

      {/* Functions List */}
      {activeLeftTab === "functions" && (
        <div className="flex-1 overflow-y-auto p-4 space-y-1">
          {functions.map((func) => {
            const Icon = func.icon;
            return (
              <button
                key={func.id}
                className={cn(
                  "w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors text-left",
                  func.active
                    ? "bg-[var(--palantir-text-accent)] text-black"
                    : "text-[var(--palantir-text-primary)] hover:bg-[var(--palantir-hover)]"
                )}
              >
                <Icon className="h-4 w-4" />
                <span>{func.name}</span>
              </button>
            );
          })}
        </div>
      )}

      {/* Buildings Section */}
      <div className="border-t border-[var(--palantir-border-primary)]">
        <button
          onClick={() => setBuildingsExpanded(!buildingsExpanded)}
          className="w-full flex items-center justify-between px-4 py-3 hover:bg-[var(--palantir-hover)] transition-colors"
        >
          <span className="text-sm font-medium text-[var(--palantir-text-primary)]">Buildings</span>
          {buildingsExpanded ? (
            <ChevronUp className="h-4 w-4 text-[var(--palantir-text-muted)]" />
          ) : (
            <ChevronDown className="h-4 w-4 text-[var(--palantir-text-muted)]" />
          )}
        </button>

        {buildingsExpanded && (
          <>
            {/* Buildings Search */}
            <div className="px-4 pb-3">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-[var(--palantir-text-muted)]" />
                <Input
                  placeholder="Q Search"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9 pr-9 h-8 text-xs bg-[var(--palantir-bg-tertiary)] border-[var(--palantir-border-primary)]"
                />
                <Filter className="absolute right-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-[var(--palantir-text-muted)]" />
              </div>
            </div>

            {/* Buildings Header */}
            <div className="px-4 pb-2 flex items-center justify-between">
              <span className="text-xs text-[var(--palantir-text-muted)]">{filteredBuildings.length} results</span>
              <div className="flex gap-1">
                <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
                  <Plus className="h-3 w-3" />
                </Button>
                <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
                  <Star className="h-3 w-3" />
                </Button>
                <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
                  <Edit className="h-3 w-3" />
                </Button>
                <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
                  <Trash2 className="h-3 w-3" />
                </Button>
              </div>
            </div>

            {/* Region Dropdown */}
            <div className="px-4 pb-3">
              <select className="w-full h-8 text-xs bg-[var(--palantir-bg-tertiary)] border border-[var(--palantir-border-primary)] rounded px-2 text-[var(--palantir-text-primary)]">
                <option>Central region</option>
                <option>North region</option>
                <option>South region</option>
              </select>
            </div>

            {/* Buildings List */}
            <div className="flex-1 overflow-y-auto px-4 pb-4 space-y-1">
              {filteredBuildings.map((building) => (
                <button
                  key={building.id}
                  onClick={() => onBuildingSelect?.(building)}
                  className={cn(
                    "w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors text-left",
                    selectedBuilding?.id === building.id
                      ? "bg-[var(--palantir-text-accent)] text-black"
                      : "text-[var(--palantir-text-primary)] hover:bg-[var(--palantir-hover)]"
                  )}
                >
                  <span className="text-lg">{building.icon}</span>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium truncate">{building.name}</div>
                    <div className="text-xs text-[var(--palantir-text-muted)] flex items-center gap-1">
                      <span>📍</span>
                      {building.location}
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

