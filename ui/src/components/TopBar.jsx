import React from "react";
import { ChevronRight, Bell, HelpCircle, Settings, User, Grid } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

export default function TopBar({ locationPath = [] }) {
  const defaultPath = ["Turkey", "Ankara", "Haymana", "Central Zone", "BMS"];
  const path = locationPath.length > 0 ? locationPath : defaultPath;

  return (
    <header className="h-14 bg-[var(--palantir-bg-secondary)] border-b border-[var(--palantir-border-primary)] px-6 flex items-center justify-between">
      {/* Left: Location Breadcrumbs */}
      <div className="flex items-center gap-2">
        <Select defaultValue="turkey">
          <SelectTrigger className="w-32 h-8 text-xs border-[var(--palantir-border-primary)]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="turkey">Turkey ✓</SelectItem>
            <SelectItem value="usa">USA</SelectItem>
            <SelectItem value="uk">UK</SelectItem>
          </SelectContent>
        </Select>
        
        {path.map((segment, index) => (
          <React.Fragment key={index}>
            <ChevronRight className="h-4 w-4 text-[var(--palantir-text-muted)]" />
            <span className="text-sm text-[var(--palantir-text-primary)]">{segment}</span>
          </React.Fragment>
        ))}
      </div>

      {/* Right: User Controls */}
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" className="h-8">
          Invite 16
        </Button>
        <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
          <Bell className="h-4 w-4" />
        </Button>
        <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
          <HelpCircle className="h-4 w-4" />
        </Button>
        <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
          <Settings className="h-4 w-4" />
        </Button>
        <div className="flex items-center gap-2 px-3 py-1 rounded-lg bg-[var(--palantir-bg-tertiary)]">
          <div className="w-8 h-8 rounded-full bg-[var(--palantir-text-accent)] flex items-center justify-center text-xs font-semibold text-black">
            AR
          </div>
          <div className="flex flex-col">
            <span className="text-xs font-medium text-[var(--palantir-text-primary)]">Alicia Roberts</span>
            <div className="flex items-center gap-2 text-xs text-[var(--palantir-text-muted)]">
              <span>25°C</span>
              <span>•</span>
              <span>10:32</span>
            </div>
          </div>
        </div>
        <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
          <Grid className="h-4 w-4" />
        </Button>
      </div>
    </header>
  );
}

