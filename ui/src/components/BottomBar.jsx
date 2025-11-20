import React, { useState } from "react";
import { MousePointer2, Move, ZoomIn, ZoomOut, Map, Ruler, MessageSquare, X, ChevronUp, ChevronDown, Compass } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";

export default function BottomBar({ 
  onToolChange, 
  activeTool = "select",
  onViewModeChange,
  viewMode = "3d",
  coordinates = { lat: "39.9334° N", lng: "32.8597° E" },
  compass = "315° NW"
}) {
  const [xOff, setXOff] = useState(false);

  const tools = [
    { id: "select", icon: MousePointer2, label: "Select" },
    { id: "pan", icon: Move, label: "Pan" },
    { id: "zoom", icon: ZoomIn, label: "Zoom" },
    { id: "map", icon: Map, label: "Map" },
    { id: "measure", icon: Ruler, label: "Measure" },
    { id: "chat", icon: MessageSquare, label: "Chat" }
  ];

  return (
    <footer className="h-12 bg-[var(--palantir-bg-secondary)] border-t border-[var(--palantir-border-primary)] px-6 flex items-center justify-between">
      {/* Left: Auto Mode */}
      <div className="flex items-center gap-3">
        <Select defaultValue="auto">
          <SelectTrigger className="w-24 h-8 text-xs border-[var(--palantir-border-primary)]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="auto">Auto</SelectItem>
            <SelectItem value="manual">Manual</SelectItem>
          </SelectContent>
        </Select>

        {/* Tools */}
        <div className="flex items-center gap-1">
          {tools.map((tool) => {
            const Icon = tool.icon;
            return (
              <Button
                key={tool.id}
                variant={activeTool === tool.id ? "default" : "ghost"}
                size="sm"
                className="h-8 w-8 p-0"
                onClick={() => onToolChange?.(tool.id)}
                title={tool.label}
              >
                <Icon className="h-4 w-4" />
              </Button>
            );
          })}
        </div>

        {/* X Off Toggle */}
        <Button
          variant={xOff ? "default" : "outline"}
          size="sm"
          className="h-8 px-3 text-xs"
          onClick={() => setXOff(!xOff)}
        >
          X {xOff ? "On" : "Off"}
        </Button>

        {/* Up/Down Arrows */}
        <div className="flex flex-col">
          <Button variant="ghost" size="sm" className="h-4 w-6 p-0">
            <ChevronUp className="h-3 w-3" />
          </Button>
          <Button variant="ghost" size="sm" className="h-4 w-6 p-0">
            <ChevronDown className="h-3 w-3" />
          </Button>
        </div>
      </div>

      {/* Center: View Mode Toggle */}
      <div className="flex items-center gap-2">
        <Button
          variant={viewMode === "3d" ? "default" : "outline"}
          size="sm"
          className="h-8 px-4 text-xs"
          onClick={() => onViewModeChange?.("3d")}
        >
          3D
        </Button>
        <Button
          variant={viewMode === "2d" ? "default" : "outline"}
          size="sm"
          className="h-8 px-4 text-xs"
          onClick={() => onViewModeChange?.("2d")}
        >
          2D
        </Button>
      </div>

      {/* Right: Compass, Coordinates */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <Compass className="h-4 w-4 text-[var(--palantir-text-muted)]" />
          <span className="text-xs text-[var(--palantir-text-muted)]">{compass}</span>
        </div>
        <div className="text-xs text-[var(--palantir-text-muted)]">
          {coordinates.lat}, {coordinates.lng}
        </div>
        <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
          <X className="h-4 w-4" />
        </Button>
      </div>
    </footer>
  );
}

