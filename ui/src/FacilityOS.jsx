import React, { useState, useCallback, useEffect, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { 
  Factory, 
  Network, 
  Send, 
  Plus, 
  FileUp, 
  CheckCircle2, 
  Wrench, 
  MessageSquare, 
  GitBranch,
  Home,
  Cuboid,
  Box,
  Clipboard,
  Search,
  Filter,
  Download,
  Upload,
  Settings,
  Bell,
  User,
  ChevronDown,
  ChevronUp,
  X,
  Minimize2,
  Maximize2
} from "lucide-react";
import ForceGraph2D from "react-force-graph-2d";
import { API_BASE } from "@/lib/env";
import { cn } from "@/lib/utils";

// === AI Assistant Component ===
const AIAssistant = ({ isExpanded, onToggle, onSendMessage }) => {
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content: "👋 Welcome to FacilityOS! I'm your AI facility manager. I can help you with:\n\n• Viewing and managing assets\n• Creating work orders\n• Analyzing facility health\n• Scheduling maintenance\n• Finding equipment issues\n\nWhat would you like to do?",
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ]);
  const [isLoading, setIsLoading] = useState(false);

  const quickCommands = [
    "Show critical assets",
    "Create work order", 
    "Asset health",
    "Maintenance schedule"
  ];

  const handleSendMessage = useCallback(async (msg = message) => {
    if (!msg.trim()) return;
    
    const userMessage = { role: "user", content: msg, timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) };
    setMessages(prev => [...prev, userMessage]);
    setMessage("");
    setIsLoading(true);

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: msg,
          history: messages.map(m => ({ role: m.role, content: m.content }))
        })
      });
      
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Chat failed");
      
      const assistantMessage = { 
        role: "assistant", 
        content: data.reply, 
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        tool: data.tool
      };
      setMessages(prev => [...prev, assistantMessage]);
      
      // Handle agentic tool actions
      if (data.tool?.action === "search") {
        onSendMessage("search", data.tool);
        // Auto-navigate to graph view for search results
        setTimeout(() => {
          const event = new CustomEvent('navigate', { detail: 'graph-view' });
          window.dispatchEvent(event);
        }, 500);
      } else if (data.tool?.action === "count") {
        onSendMessage("count", data.tool);
        // Auto-navigate to assets view for count results
        setTimeout(() => {
          const event = new CustomEvent('navigate', { detail: 'assets' });
          window.dispatchEvent(event);
        }, 500);
      } else if (data.tool?.action === "work-order") {
        onSendMessage("work-order", data.tool);
        // Auto-navigate to work orders view
        setTimeout(() => {
          const event = new CustomEvent('navigate', { detail: 'work-orders' });
          window.dispatchEvent(event);
        }, 500);
      }
    } catch (error) {
      console.error("Chat error:", error);
      const errorMessage = { 
        role: "assistant", 
        content: `Sorry, I encountered an error: ${error.message}`, 
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  }, [message, messages, onSendMessage]);

  const handleQuickCommand = (cmd) => {
    handleSendMessage(cmd);
  };

  if (!isExpanded) {
    return (
      <div className="fixed bottom-6 right-6 z-50">
        <Button
          onClick={onToggle}
          className="h-14 w-14 rounded-full bg-[var(--palantir-text-accent)] hover:bg-[var(--palantir-info)] shadow-lg"
        >
          <MessageSquare className="h-6 w-6 text-white" />
        </Button>
      </div>
    );
  }

  return (
    <div className="fixed bottom-6 right-6 z-50 w-96 h-[600px] bg-[var(--palantir-bg-elevated)] border border-[var(--palantir-border-primary)] rounded-xl shadow-xl">
      <div className="flex items-center justify-between p-4 border-b border-[var(--palantir-border-primary)]">
        <div className="flex items-center gap-2">
          <MessageSquare className="h-5 w-5 text-[var(--palantir-text-accent)]" />
          <h3 className="font-semibold text-[var(--palantir-text-primary)]">AI Assistant</h3>
          <Badge className="bg-[var(--palantir-success)] text-black text-xs">Always On</Badge>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
            <Minimize2 className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="sm" className="h-8 w-8 p-0" onClick={onToggle}>
            <X className="h-4 w-4" />
          </Button>
        </div>
      </div>
      
      <div className="flex flex-col h-full">
        <div className="p-4 border-b border-[var(--palantir-border-primary)]">
          <p className="text-sm text-[var(--palantir-text-secondary)] mb-3">
            Your AI-powered facility management assistant
          </p>
          
          <div className="space-y-2">
            <div className="bg-[var(--palantir-bg-secondary)] rounded-lg p-3 text-sm">
              {messages[messages.length - 1]?.content}
            </div>
            <div className="text-xs text-[var(--palantir-text-muted)]">
              {messages[messages.length - 1]?.timestamp}
            </div>
          </div>
        </div>

        <div className="p-4">
          <div className="mb-4">
            <Label className="text-sm font-medium text-[var(--palantir-text-primary)] mb-2 block">
              Quick Commands:
            </Label>
            <div className="grid grid-cols-2 gap-2">
              {quickCommands.map((cmd) => (
                <Button
                  key={cmd}
                  variant="outline"
                  size="sm"
                  className="text-xs justify-start"
                  onClick={() => handleQuickCommand(cmd)}
                >
                  {cmd}
                </Button>
              ))}
            </div>
          </div>
        </div>

        <div className="mt-auto p-4 border-t border-[var(--palantir-border-primary)]">
          <div className="space-y-2">
            <Input
              placeholder="Ask me anything about your facility..."
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
              className="bg-[var(--palantir-bg-secondary)] border-[var(--palantir-border-primary)]"
            />
            <div className="text-xs text-[var(--palantir-text-muted)]">
              💡 Try: "Show critical assets" or "Create work order for HVAC"
            </div>
            <Button 
              onClick={() => handleSendMessage()} 
              disabled={isLoading || !message.trim()}
              className="w-full bg-[var(--palantir-text-accent)] hover:bg-[var(--palantir-info)]"
            >
              {isLoading ? "Thinking..." : "Send"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

// === Navigation Component ===
const Navigation = ({ activeTab, onTabChange }) => {
  const navItems = [
    { id: "dashboard", label: "Dashboard", icon: Home },
    { id: "3d-viewer", label: "3D Model Viewer", icon: Cuboid },
    { id: "graph-view", label: "Graph View", icon: Network },
    { id: "assets", label: "Assets", icon: Box },
    { id: "work-orders", label: "Work Orders", icon: Clipboard }
  ];

  return (
    <div className="w-64 bg-[var(--palantir-bg-secondary)] border-r border-[var(--palantir-border-primary)] h-full">
      <div className="p-6 border-b border-[var(--palantir-border-primary)]">
        <div className="flex items-center gap-3">
          <Factory className="h-8 w-8 text-[var(--palantir-text-accent)]" />
          <h1 className="text-xl font-bold text-[var(--palantir-text-primary)]">FacilityOS</h1>
        </div>
      </div>
      
      <div className="p-4">
        <h2 className="text-sm font-medium text-[var(--palantir-text-secondary)] mb-4">Navigation</h2>
        <nav className="space-y-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                onClick={() => onTabChange(item.id)}
                className={cn(
                  "w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left transition-colors",
                  activeTab === item.id
                    ? "bg-[var(--palantir-text-accent)] text-black"
                    : "text-[var(--palantir-text-primary)] hover:bg-[var(--palantir-hover)]"
                )}
              >
                <Icon className="h-5 w-5" />
                <span className="text-sm font-medium">{item.label}</span>
              </button>
            );
          })}
        </nav>
      </div>
    </div>
  );
};

// === Dashboard View ===
const DashboardView = ({ onAIAction }) => {
  const [metrics, setMetrics] = useState({
    totalAssets: 0,
    activeWorkOrders: 0,
    criticalAlerts: 0,
    completedTasks: 0
  });

  const [recentActivity, setRecentActivity] = useState([]);
  const [facilityHealth, setFacilityHealth] = useState({});

  useEffect(() => {
    // Load dashboard data
    const loadDashboardData = async () => {
      try {
        // Load work orders for metrics
        const woRes = await fetch(`${API_BASE}/workorders`);
        const workOrders = await woRes.json();
        
        // Load asset count
        const countRes = await fetch(`${API_BASE}/count?q=assets`);
        const countData = await countRes.json();
        
        setMetrics({
          totalAssets: countData.total || 0,
          activeWorkOrders: workOrders.filter(wo => wo.status === "Open").length,
          criticalAlerts: workOrders.filter(wo => wo.priority === "Critical").length,
          completedTasks: workOrders.filter(wo => wo.status === "Done").length
        });
      } catch (error) {
        console.error("Failed to load dashboard data:", error);
      }
    };

    loadDashboardData();
  }, []);

  return (
    <div className="flex-1 p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-[var(--palantir-text-primary)]">Facility Overview</h1>
          <p className="text-[var(--palantir-text-secondary)] mt-2">
            Ask the AI assistant anything about your facility →
          </p>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-4 gap-6">
        <Card className="palantir-card">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-[var(--palantir-text-muted)]">Total Assets</p>
                <p className="text-2xl font-bold text-[var(--palantir-text-primary)]">{metrics.totalAssets}</p>
                <p className="text-xs text-[var(--palantir-text-accent)] mt-1">Ask AI: "Show asset breakdown"</p>
              </div>
              <Box className="h-8 w-8 text-[var(--palantir-text-accent)]" />
            </div>
          </CardContent>
        </Card>

        <Card className="palantir-card">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-[var(--palantir-text-muted)]">Active Work Orders</p>
                <p className="text-2xl font-bold text-[var(--palantir-text-primary)]">{metrics.activeWorkOrders}</p>
                <p className="text-xs text-[var(--palantir-text-accent)] mt-1">Try: "Create work order"</p>
              </div>
              <Wrench className="h-8 w-8 text-[var(--palantir-text-accent)]" />
            </div>
          </CardContent>
        </Card>

        <Card className="palantir-card">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-[var(--palantir-text-muted)]">Critical Alerts</p>
                <p className="text-2xl font-bold text-[var(--palantir-error)]">{metrics.criticalAlerts}</p>
                <p className="text-xs text-[var(--palantir-text-muted)] mt-1">Requires attention</p>
              </div>
              <Bell className="h-8 w-8 text-[var(--palantir-error)]" />
            </div>
          </CardContent>
        </Card>

        <Card className="palantir-card">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-[var(--palantir-text-muted)]">Completed Tasks</p>
                <p className="text-2xl font-bold text-[var(--palantir-success)]">{metrics.completedTasks}</p>
                <p className="text-xs text-[var(--palantir-text-muted)] mt-1">This month</p>
              </div>
              <CheckCircle2 className="h-8 w-8 text-[var(--palantir-success)]" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Activity & Facility Health */}
      <div className="grid grid-cols-2 gap-6">
        <Card className="palantir-card">
          <CardHeader>
            <CardTitle className="text-lg">Recent Activity</CardTitle>
            <p className="text-sm text-[var(--palantir-text-muted)]">Latest updates from your facility</p>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {recentActivity.length > 0 ? (
                recentActivity.map((activity, index) => (
                  <div key={index} className="flex items-center gap-3">
                    <div className={cn(
                      "w-2 h-2 rounded-full",
                      activity.status === "completed" ? "bg-[var(--palantir-success)]" :
                      activity.status === "scheduled" ? "bg-[var(--palantir-info)]" :
                      activity.status === "critical" ? "bg-[var(--palantir-error)]" :
                      "bg-[var(--palantir-warning)]"
                    )} />
                    <div className="flex-1">
                      <p className="text-sm font-medium text-[var(--palantir-text-primary)]">{activity.asset}</p>
                      <p className="text-xs text-[var(--palantir-text-muted)]">{activity.action}</p>
                    </div>
                    <p className="text-xs text-[var(--palantir-text-muted)]">{activity.time}</p>
                  </div>
                ))
              ) : (
                <p className="text-sm text-[var(--palantir-text-muted)]">No recent activity</p>
              )}
            </div>
          </CardContent>
        </Card>

        <Card className="palantir-card">
          <CardHeader>
            <CardTitle className="text-lg">Facility Health</CardTitle>
            <p className="text-sm text-[var(--palantir-text-muted)]">System status overview</p>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {Object.entries(facilityHealth).map(([system, health]) => (
                <div key={system}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-[var(--palantir-text-primary)]">{system}</span>
                    <span className="text-[var(--palantir-text-muted)]">{health}%</span>
                  </div>
                  <div className="w-full bg-[var(--palantir-bg-tertiary)] rounded-full h-2">
                    <div 
                      className={cn(
                        "h-2 rounded-full",
                        health >= 95 ? "bg-[var(--palantir-success)]" :
                        health >= 85 ? "bg-[var(--palantir-warning)]" :
                        "bg-[var(--palantir-error)]"
                      )}
                      style={{ width: `${health}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

// === 3D Model Viewer ===
const ModelViewer3D = () => {
  const [isModelLoaded, setIsModelLoaded] = useState(false);
  const fileInputRef = useRef(null);

  const handleFileUpload = (event) => {
    const file = event.target.files[0];
    if (file) {
      setIsModelLoaded(true);
      // TODO: Implement actual IFC loading
    }
  };

  return (
    <div className="flex-1 p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-[var(--palantir-text-primary)]">3D Model Viewer</h1>
          <p className="text-[var(--palantir-text-secondary)] mt-2">
            View and interact with your facility's BIM model
          </p>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" className="flex items-center gap-2">
            <Download className="h-4 w-4" />
            Export
          </Button>
          <Button className="bg-[var(--palantir-text-accent)] hover:bg-[var(--palantir-info)] flex items-center gap-2">
            <Upload className="h-4 w-4" />
            Upload IFC
          </Button>
        </div>
      </div>

      <Card className="palantir-card-elevated h-[600px]">
        <CardHeader>
          <CardTitle>BIM Model</CardTitle>
          <p className="text-sm text-[var(--palantir-text-muted)]">Industry Foundation Classes (IFC) viewer</p>
        </CardHeader>
        <CardContent className="h-full flex items-center justify-center">
          {!isModelLoaded ? (
            <div className="text-center space-y-4">
              <Upload className="h-16 w-16 text-[var(--palantir-text-muted)] mx-auto" />
              <div>
                <h3 className="text-lg font-semibold text-[var(--palantir-text-primary)]">No model loaded</h3>
                <p className="text-[var(--palantir-text-muted)]">Upload an IFC file to begin</p>
              </div>
              <Button 
                onClick={() => fileInputRef.current?.click()}
                className="bg-[var(--palantir-text-accent)] hover:bg-[var(--palantir-info)]"
              >
                <Upload className="h-4 w-4 mr-2" />
                Upload IFC File
              </Button>
              <input
                ref={fileInputRef}
                type="file"
                accept=".ifc"
                onChange={handleFileUpload}
                className="hidden"
              />
            </div>
          ) : (
            <div className="w-full h-full bg-[var(--palantir-bg-tertiary)] rounded-lg flex items-center justify-center">
              <p className="text-[var(--palantir-text-muted)]">3D Model Viewer Placeholder</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Model Info Panels */}
      {isModelLoaded && (
        <div className="grid grid-cols-3 gap-4">
          <Card className="palantir-card">
            <CardContent className="p-4">
              <h3 className="font-semibold text-[var(--palantir-text-primary)] mb-2">Model Info</h3>
              <div className="space-y-1 text-sm">
                <div className="flex justify-between">
                  <span className="text-[var(--palantir-text-muted)]">Elements:</span>
                  <span className="text-[var(--palantir-text-primary)]">12,847</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[var(--palantir-text-muted)]">Floors:</span>
                  <span className="text-[var(--palantir-text-primary)]">8</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[var(--palantir-text-muted)]">Spaces:</span>
                  <span className="text-[var(--palantir-text-primary)]">156</span>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="palantir-card">
            <CardContent className="p-4">
              <h3 className="font-semibold text-[var(--palantir-text-primary)] mb-2">Active Layers</h3>
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-blue-500 rounded"></div>
                  <span className="text-sm text-[var(--palantir-text-primary)]">Structural</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-purple-500 rounded"></div>
                  <span className="text-sm text-[var(--palantir-text-primary)]">Mechanical</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-green-500 rounded"></div>
                  <span className="text-sm text-[var(--palantir-text-primary)]">Electrical</span>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="palantir-card">
            <CardContent className="p-4">
              <h3 className="font-semibold text-[var(--palantir-text-primary)] mb-2">Selection</h3>
              <div className="space-y-1 text-sm">
                <div className="flex justify-between">
                  <span className="text-[var(--palantir-text-muted)]">Type:</span>
                  <span className="text-[var(--palantir-text-primary)]">HVAC Unit</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[var(--palantir-text-muted)]">ID:</span>
                  <span className="text-[var(--palantir-text-primary)]">HVAC-3A-02</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[var(--palantir-text-muted)]">Status:</span>
                  <span className="text-[var(--palantir-success)]">Operational</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
};

// === Graph View ===
const GraphView = ({ onAIAction }) => {
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [selectedNode, setSelectedNode] = useState(null);
  const containerRef = useRef(null);
  const [size, setSize] = useState({ width: 0, height: 0 });

  useEffect(() => {
    // Load initial graph data
    const loadGraphData = async () => {
      try {
        const res = await fetch(`${API_BASE}/search?q=facility structure&k=20&hops=2`);
        const data = await res.json();
        
        if (res.ok && data.subgraphs) {
          const nodes = [];
          const links = [];
          const seen = new Set();

          data.subgraphs.forEach((sg) => {
            sg.nodes?.forEach((n) => {
              if (seen.has(n.id)) return;
              seen.add(n.id);
              nodes.push({
                id: n.id,
                name: n.name || "(unnamed)",
                type: n.type || "",
                labels: n.labels || []
              });
            });
            
            sg.edges?.forEach((e) => {
              links.push({
                source: e.src,
                target: e.dst,
                type: e.type
              });
            });
          });

          setGraphData({ nodes, links });
        }
      } catch (error) {
        console.error("Failed to load graph data:", error);
      }
    };

    loadGraphData();
  }, []);

  useEffect(() => {
    const el = containerRef.current;
    if (!el || typeof ResizeObserver === "undefined") return;

    const updateSize = () => {
      setSize({ width: el.clientWidth, height: el.clientHeight });
    };
    updateSize();

    const observer = new ResizeObserver(() => updateSize());
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const drawNode = useCallback((node, ctx, scale) => {
    const radius = 8;
    ctx.beginPath();
    ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI, false);
    
    // Color by type
    ctx.fillStyle = node.type?.includes("Building") ? "#00d4ff" :
                   node.type?.includes("Storey") ? "#8b5cf6" :
                   node.type?.includes("Space") ? "#34d399" :
                   "#e2e8f0";
    
    ctx.fill();
    ctx.font = `${Math.max(12 / scale, 8)}px Inter, system-ui`;
    ctx.fillStyle = "#ffffff";
    const label = node.name?.slice(0, 20) || node.id.slice(0, 8);
    ctx.fillText(label, node.x + radius + 4, node.y + 4);
  }, []);

  return (
    <div className="flex-1 p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-[var(--palantir-text-primary)]">Graph View</h1>
          <p className="text-[var(--palantir-text-secondary)] mt-2">
            Explore facility relationships and dependencies
          </p>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" className="flex items-center gap-2">
            <Filter className="h-4 w-4" />
            Filter
          </Button>
          <Button variant="outline" className="flex items-center gap-2">
            <Maximize2 className="h-4 w-4" />
            Expand All
          </Button>
          <Button variant="outline" className="flex items-center gap-2">
            <Download className="h-4 w-4" />
            Export
          </Button>
        </div>
      </div>

      <Card className="palantir-card-elevated h-[600px]">
        <CardHeader>
          <CardTitle>Facility Graph Network</CardTitle>
          <p className="text-sm text-[var(--palantir-text-muted)]">Neo4j-style relationship visualization</p>
        </CardHeader>
        <CardContent className="h-full p-0">
          <div ref={containerRef} className="h-full w-full">
            {size.width > 0 && size.height > 0 && (
              <ForceGraph2D
                graphData={graphData}
                nodeId="id"
                nodeCanvasObject={drawNode}
                linkDirectionalArrowLength={4}
                linkColor={() => "#94a3b8"}
                onNodeClick={(node) => setSelectedNode(node)}
                width={size.width}
                height={size.height}
              />
            )}
          </div>
        </CardContent>
      </Card>

      {/* Node Details & Relationships */}
      {selectedNode && (
        <div className="grid grid-cols-2 gap-6">
          <Card className="palantir-card">
            <CardHeader>
              <CardTitle>Node Details</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-[var(--palantir-text-muted)]">Selected:</span>
                  <span className="text-[var(--palantir-text-primary)]">{selectedNode.name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[var(--palantir-text-muted)]">Type:</span>
                  <span className="text-[var(--palantir-text-primary)]">{selectedNode.type}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[var(--palantir-text-muted)]">Connections:</span>
                  <span className="text-[var(--palantir-text-primary)]">
                    {graphData.links.filter(l => l.source === selectedNode.id || l.target === selectedNode.id).length} relationships
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="palantir-card">
            <CardHeader>
              <CardTitle>Relationships</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2 text-sm">
                {graphData.links
                  .filter(l => l.source === selectedNode.id || l.target === selectedNode.id)
                  .slice(0, 3)
                  .map((link, index) => (
                    <div key={index} className="flex justify-between">
                      <span className="text-[var(--palantir-text-primary)]">
                        {link.type} → {link.source === selectedNode.id ? 
                          graphData.nodes.find(n => n.id === link.target)?.name : 
                          graphData.nodes.find(n => n.id === link.source)?.name}
                      </span>
                    </div>
                  ))}
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
};

// === Assets View ===
const AssetsView = ({ onAIAction }) => {
  const [assets, setAssets] = useState([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [filteredAssets, setFilteredAssets] = useState([]);

  useEffect(() => {
    const loadAssets = async () => {
      try {
        // Load asset count and types
        const res = await fetch(`${API_BASE}/count?q=assets`);
        const data = await res.json();
        
        // For now, create mock data based on the count
        const mockAssets = [
          { id: "HVAC-3A-02", name: "HVAC Unit 3A", type: "HVAC", location: "Floor 3", status: "operational", lastMaintenance: "2025-09-15" },
          { id: "ELEV-01", name: "Passenger Elevator 1", type: "Elevator", location: "Core", status: "operational", lastMaintenance: "2025-09-20" },
          { id: "FIRE-2B", name: "Fire Panel 2B", type: "Fire Safety", location: "Floor 2", status: "warning", lastMaintenance: "2025-08-10" },
          { id: "LIGHT-5A", name: "LED Lighting Zone 5A", type: "Lighting", location: "Floor 5", status: "operational", lastMaintenance: "2025-09-25" },
          { id: "HVAC-1B-01", name: "HVAC Unit 1B", type: "HVAC", location: "Floor 1", status: "critical", lastMaintenance: "2025-07-15" }
        ];
        
        setAssets(mockAssets);
        setFilteredAssets(mockAssets);
      } catch (error) {
        console.error("Failed to load assets:", error);
      }
    };

    loadAssets();
  }, []);

  useEffect(() => {
    const filtered = assets.filter(asset =>
      asset.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      asset.type.toLowerCase().includes(searchTerm.toLowerCase()) ||
      asset.location.toLowerCase().includes(searchTerm.toLowerCase())
    );
    setFilteredAssets(filtered);
  }, [searchTerm, assets]);

  const getStatusColor = (status) => {
    switch (status) {
      case "operational": return "bg-[var(--palantir-success)] text-black";
      case "warning": return "bg-[var(--palantir-warning)] text-black";
      case "critical": return "bg-[var(--palantir-error)] text-white";
      default: return "bg-[var(--palantir-text-muted)] text-white";
    }
  };

  return (
    <div className="flex-1 p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-[var(--palantir-text-primary)]">Assets</h1>
          <p className="text-[var(--palantir-text-secondary)] mt-2">
            Manage facility equipment and systems
          </p>
        </div>
        <Button className="bg-[var(--palantir-text-accent)] hover:bg-[var(--palantir-info)] flex items-center gap-2">
          <Plus className="h-4 w-4" />
          Add Asset
        </Button>
      </div>

      <Card className="palantir-card">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Asset Inventory</CardTitle>
              <p className="text-sm text-[var(--palantir-text-muted)]">{filteredAssets.length} assets total</p>
            </div>
            <div className="flex gap-3">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-[var(--palantir-text-muted)]" />
                <Input
                  placeholder="Search assets..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10 w-64 bg-[var(--palantir-bg-secondary)] border-[var(--palantir-border-primary)]"
                />
              </div>
              <Button variant="outline" className="flex items-center gap-2">
                <Filter className="h-4 w-4" />
                Filter
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-[var(--palantir-border-primary)]">
                  <th className="text-left py-3 px-4 text-sm font-medium text-[var(--palantir-text-primary)]">Asset ID</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-[var(--palantir-text-primary)]">Name</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-[var(--palantir-text-primary)]">Type</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-[var(--palantir-text-primary)]">Location</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-[var(--palantir-text-primary)]">Status</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-[var(--palantir-text-primary)]">Last Maintenance</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-[var(--palantir-text-primary)]"></th>
                </tr>
              </thead>
              <tbody>
                {filteredAssets.map((asset) => (
                  <tr key={asset.id} className="border-b border-[var(--palantir-border-primary)] hover:bg-[var(--palantir-hover)]">
                    <td className="py-3 px-4">
                      <span className="text-[var(--palantir-text-accent)] font-mono text-sm">{asset.id}</span>
                    </td>
                    <td className="py-3 px-4 text-sm text-[var(--palantir-text-primary)]">{asset.name}</td>
                    <td className="py-3 px-4 text-sm text-[var(--palantir-text-primary)]">{asset.type}</td>
                    <td className="py-3 px-4 text-sm text-[var(--palantir-text-primary)]">{asset.location}</td>
                    <td className="py-3 px-4">
                      <Badge className={getStatusColor(asset.status)}>
                        {asset.status}
                      </Badge>
                    </td>
                    <td className="py-3 px-4 text-sm text-[var(--palantir-text-muted)]">{asset.lastMaintenance}</td>
                    <td className="py-3 px-4">
                      <Button variant="ghost" size="sm">
                        <Settings className="h-4 w-4" />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Summary Cards */}
      <div className="grid grid-cols-3 gap-6">
        <Card className="palantir-card">
          <CardContent className="p-4">
            <h3 className="font-semibold text-[var(--palantir-text-primary)] mb-3">By Status</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-[var(--palantir-text-muted)]">Operational</span>
                <span className="text-[var(--palantir-success)]">{assets.filter(a => a.status === "operational").length}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--palantir-text-muted)]">Warning</span>
                <span className="text-[var(--palantir-warning)]">{assets.filter(a => a.status === "warning").length}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--palantir-text-muted)]">Critical</span>
                <span className="text-[var(--palantir-error)]">{assets.filter(a => a.status === "critical").length}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="palantir-card">
          <CardContent className="p-4">
            <h3 className="font-semibold text-[var(--palantir-text-primary)] mb-3">By Type</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-[var(--palantir-text-muted)]">HVAC</span>
                <span className="text-[var(--palantir-text-primary)]">{assets.filter(a => a.type === "HVAC").length}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--palantir-text-muted)]">Fire Safety</span>
                <span className="text-[var(--palantir-text-primary)]">{assets.filter(a => a.type === "Fire Safety").length}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--palantir-text-muted)]">Other</span>
                <span className="text-[var(--palantir-text-primary)]">{assets.filter(a => !["HVAC", "Fire Safety"].includes(a.type)).length}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="palantir-card">
          <CardContent className="p-4">
            <h3 className="font-semibold text-[var(--palantir-text-primary)] mb-3">Maintenance Due</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-[var(--palantir-text-muted)]">This Week</span>
                <span className="text-[var(--palantir-warning)]">2</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--palantir-text-muted)]">This Month</span>
                <span className="text-[var(--palantir-info)]">5</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--palantir-text-muted)]">Overdue</span>
                <span className="text-[var(--palantir-error)]">1</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

// === Work Orders View ===
const WorkOrdersView = ({ onAIAction }) => {
  const [workOrders, setWorkOrders] = useState([]);
  const [searchTerm, setSearchTerm] = useState("");

  useEffect(() => {
    const loadWorkOrders = async () => {
      try {
        const res = await fetch(`${API_BASE}/workorders`);
        const data = await res.json();
        setWorkOrders(data || []);
      } catch (error) {
        console.error("Failed to load work orders:", error);
      }
    };

    loadWorkOrders();
  }, []);

  const getPriorityColor = (priority) => {
    switch (priority) {
      case "Critical": return "bg-[var(--palantir-error)] text-white";
      case "High": return "bg-[var(--palantir-error)] text-white";
      case "Medium": return "bg-[var(--palantir-warning)] text-black";
      case "Low": return "bg-[var(--palantir-info)] text-white";
      default: return "bg-[var(--palantir-text-muted)] text-white";
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case "Open": return "bg-[var(--palantir-info)] text-white";
      case "In Progress": return "bg-[var(--palantir-warning)] text-black";
      case "Done": return "bg-[var(--palantir-success)] text-black";
      default: return "bg-[var(--palantir-text-muted)] text-white";
    }
  };

  return (
    <div className="flex-1 p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-[var(--palantir-text-primary)]">Work Orders</h1>
          <p className="text-[var(--palantir-text-secondary)] mt-2">
            Track and manage maintenance tasks
          </p>
        </div>
        <Button className="bg-[var(--palantir-text-accent)] hover:bg-[var(--palantir-info)] flex items-center gap-2">
          <Plus className="h-4 w-4" />
          Create Work Order
        </Button>
      </div>

      <Card className="palantir-card">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Active Work Orders</CardTitle>
              <p className="text-sm text-[var(--palantir-text-muted)]">{workOrders.length} work orders</p>
            </div>
            <div className="flex gap-3">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-[var(--palantir-text-muted)]" />
                <Input
                  placeholder="Search work orders..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10 w-64 bg-[var(--palantir-bg-secondary)] border-[var(--palantir-border-primary)]"
                />
              </div>
              <Button variant="outline" className="flex items-center gap-2">
                <Filter className="h-4 w-4" />
                Filter
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-[var(--palantir-border-primary)]">
                  <th className="text-left py-3 px-4 text-sm font-medium text-[var(--palantir-text-primary)]">ID</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-[var(--palantir-text-primary)]">Title</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-[var(--palantir-text-primary)]">Priority</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-[var(--palantir-text-primary)]">Status</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-[var(--palantir-text-primary)]">Assignee</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-[var(--palantir-text-primary)]">Due Date</th>
                </tr>
              </thead>
              <tbody>
                {workOrders.map((wo) => (
                  <tr key={wo.id} className="border-b border-[var(--palantir-border-primary)] hover:bg-[var(--palantir-hover)]">
                    <td className="py-3 px-4">
                      <span className="text-[var(--palantir-text-accent)] font-mono text-sm">{wo.id}</span>
                    </td>
                    <td className="py-3 px-4 text-sm text-[var(--palantir-text-primary)]">{wo.title}</td>
                    <td className="py-3 px-4">
                      <Badge className={getPriorityColor(wo.priority)}>
                        {wo.priority}
                      </Badge>
                    </td>
                    <td className="py-3 px-4">
                      <Badge className={getStatusColor(wo.status)}>
                        {wo.status}
                      </Badge>
                    </td>
                    <td className="py-3 px-4 text-sm text-[var(--palantir-text-primary)]">Unassigned</td>
                    <td className="py-3 px-4 text-sm text-[var(--palantir-text-muted)]">
                      {wo.createdAt ? new Date(wo.createdAt).toLocaleDateString() : "TBD"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Summary Cards */}
      <div className="grid grid-cols-4 gap-6">
        <Card className="palantir-card">
          <CardContent className="p-4">
            <h3 className="font-semibold text-[var(--palantir-text-primary)] mb-3">By Status</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-[var(--palantir-text-muted)]">Pending</span>
                <span className="text-[var(--palantir-text-primary)]">{workOrders.filter(wo => wo.status === "Open").length}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--palantir-text-muted)]">In Progress</span>
                <span className="text-[var(--palantir-text-primary)]">{workOrders.filter(wo => wo.status === "In Progress").length}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--palantir-text-muted)]">Completed</span>
                <span className="text-[var(--palantir-text-primary)]">{workOrders.filter(wo => wo.status === "Done").length}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="palantir-card">
          <CardContent className="p-4">
            <h3 className="font-semibold text-[var(--palantir-text-primary)] mb-3">By Priority</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-[var(--palantir-text-muted)]">High</span>
                <span className="text-[var(--palantir-error)]">{workOrders.filter(wo => wo.priority === "High" || wo.priority === "Critical").length}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--palantir-text-muted)]">Medium</span>
                <span className="text-[var(--palantir-warning)]">{workOrders.filter(wo => wo.priority === "Medium").length}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--palantir-text-muted)]">Low</span>
                <span className="text-[var(--palantir-info)]">{workOrders.filter(wo => wo.priority === "Low").length}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="palantir-card">
          <CardContent className="p-4">
            <h3 className="font-semibold text-[var(--palantir-text-primary)] mb-3">Due This Week</h3>
            <div className="text-center">
              <div className="text-3xl font-bold text-[var(--palantir-text-primary)]">4</div>
              <div className="text-sm text-[var(--palantir-text-muted)]">2 overdue</div>
            </div>
          </CardContent>
        </Card>

        <Card className="palantir-card">
          <CardContent className="p-4">
            <h3 className="font-semibold text-[var(--palantir-text-primary)] mb-3">Avg. Completion</h3>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-3xl font-bold text-[var(--palantir-text-primary)]">3.2</div>
                <div className="text-sm text-[var(--palantir-text-muted)]">days</div>
              </div>
              <MessageSquare className="h-8 w-8 text-[var(--palantir-text-accent)]" />
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

// === Main FacilityOS Component ===
export default function FacilityOS() {
  const [activeTab, setActiveTab] = useState("dashboard");
  const [aiExpanded, setAiExpanded] = useState(false);

  const handleAIAction = useCallback((action, data) => {
    // Handle AI actions - switch tabs, update data, etc.
    switch (action) {
      case "search":
        setActiveTab("graph-view");
        break;
      case "count":
        setActiveTab("assets");
        break;
      case "work-order":
        setActiveTab("work-orders");
        break;
      default:
        break;
    }
  }, []);

  // Listen for navigation events from AI assistant
  useEffect(() => {
    const handleNavigate = (event) => {
      setActiveTab(event.detail);
    };

    window.addEventListener('navigate', handleNavigate);
    return () => window.removeEventListener('navigate', handleNavigate);
  }, []);

  const renderActiveView = () => {
    switch (activeTab) {
      case "dashboard":
        return <DashboardView onAIAction={handleAIAction} />;
      case "3d-viewer":
        return <ModelViewer3D />;
      case "graph-view":
        return <GraphView onAIAction={handleAIAction} />;
      case "assets":
        return <AssetsView onAIAction={handleAIAction} />;
      case "work-orders":
        return <WorkOrdersView onAIAction={handleAIAction} />;
      default:
        return <DashboardView onAIAction={handleAIAction} />;
    }
  };

  return (
    <div className="min-h-screen bg-[var(--palantir-bg-primary)] text-[var(--palantir-text-primary)]">
      {/* Header */}
      <header className="bg-[var(--palantir-bg-secondary)] border-b border-[var(--palantir-border-primary)] px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Factory className="h-6 w-6 text-[var(--palantir-text-accent)]" />
            <h1 className="text-xl font-semibold">FacilityOS</h1>
          </div>
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-medium">Facility Management System</h2>
            <Badge className="bg-[var(--palantir-text-accent)] text-black">
              <MessageSquare className="h-3 w-3 mr-1" />
              AI-Powered CMMS
            </Badge>
          </div>
        </div>
      </header>

      {/* Main Layout */}
      <div className="flex h-[calc(100vh-80px)]">
        <Navigation activeTab={activeTab} onTabChange={setActiveTab} />
        <main className="flex-1 overflow-y-auto">
          {renderActiveView()}
        </main>
      </div>

      {/* AI Assistant */}
      <AIAssistant 
        isExpanded={aiExpanded} 
        onToggle={() => setAiExpanded(!aiExpanded)}
        onSendMessage={handleAIAction}
      />
    </div>
  );
}
