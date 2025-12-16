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
  Maximize2,
  Bot,
  Activity,
  Link as LinkIcon
} from "lucide-react";
import ForceGraph2D from "react-force-graph-2d";
import { API_BASE } from "@/lib/env";
import { cn } from "@/lib/utils";
import DirectUploadComponent from "@/components/DirectUploadComponent";
import TelemetryDashboard from "@/components/TelemetryDashboard";
import AgentDashboard from "@/components/AgentDashboard";
import EnterpriseView from "@/components/EnterpriseView";

// === AI Assistant Component ===
const AIAssistant = ({ isExpanded, onToggle, onSendMessage }) => {
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content: "👋 Welcome to RiG Digital Twin! I'm your AI assistant for the semantically normalized IWMS platform.\n\n**Agent-Based Architecture:**\n• Detection Agent monitors telemetry for issues\n• Diagnosis Agent analyzes events and generates hypotheses\n• Recommendation Agent proposes validated actions\n\n**Capabilities:**\n• Explore semantic graph (IFC-LD + 223P + Brick + SSN/SOSA + QUDT)\n• Query live telemetry from TimescaleDB\n• Execute BACnet control operations (with approval)\n• Generate work orders from agent recommendations\n• **Enterprise Graph**: Cross-domain queries (Controls, HR, Finance, Assets, Scheduling, Network)\n\n**Try:** \"Run detection on Zone_Main\", \"Show me all BACnet bindings\", or \"Find AHU-3 across all domains\"",
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ]);
  const [isLoading, setIsLoading] = useState(false);

  const quickCommands = [
    "Show house structure",
    "Find all doors", 
    "List rooms",
    "Create work order"
  ];

  const handleSendMessage = useCallback(async (msg = message) => {
    if (!msg.trim()) return;
    
    const userMessage = { role: "user", content: msg, timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) };
    setMessages(prev => [...prev, userMessage]);
    setMessage("");
    setIsLoading(true);

    try {
      console.log("Sending message to AI:", msg);
      const res = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: msg,
          history: messages.map(m => ({ role: m.role, content: m.content }))
        })
      });
      
      if (!res.ok) {
        throw new Error(`API request failed: ${res.status} ${res.statusText}`);
      }
      
      const data = await res.json();
      console.log("AI response received:", data);
      
      const assistantMessage = { 
        role: "assistant", 
        content: data.reply || "I received your message but couldn't generate a proper response.", 
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
      
      // Provide helpful fallback responses based on the message
      let fallbackResponse = "I'm having trouble connecting to the AI service right now, but I can still help! ";
      
      const msgLower = msg.toLowerCase();
      
      if (msgLower.includes("house") || msgLower.includes("structure") || msgLower.includes("building")) {
        fallbackResponse += "🏠 **Sample House Overview:**\n\n• **Ground Floor:** Living Room, Kitchen\n• **First Floor:** Bedroom 1, Bedroom 2, Bathroom\n• **Structure:** Multiple walls, doors, and windows\n• **Systems:** HVAC, Electrical, Plumbing, Fire Safety\n\n**Try these tabs:**\n• **Graph View** - Explore relationships between components\n• **Assets** - View all building systems";
      } else if (msgLower.includes("door") || msgLower.includes("window")) {
        fallbackResponse += "🚪 **Doors & Windows:**\n\n• **Front Door** - Main entrance\n• **Bedroom Door** - Interior door\n• **Living Room Window** - Large window\n• **Kitchen Window** - Smaller window\n\n**Explore in:**\n• **Graph View** - See connections to rooms";
      } else if (msgLower.includes("work order") || msgLower.includes("maintenance") || msgLower.includes("repair")) {
        fallbackResponse += "🔧 **Work Orders & Maintenance:**\n\n**Current Work Orders:**\n• HVAC Maintenance - Ground Floor (High Priority)\n• Replace Kitchen Faucet (In Progress)\n• Fire Safety Inspection (Critical)\n• Security Camera Check (Open)\n\n**Go to:**\n• **Work Orders tab** - Manage all maintenance tasks\n• **Assets tab** - View equipment status";
      } else if (msgLower.includes("hvac") || msgLower.includes("heating") || msgLower.includes("cooling")) {
        fallbackResponse += "🌡️ **HVAC Systems:**\n\n• **HVAC Unit Ground Floor** - Operational\n• **HVAC Unit First Floor** - Operational\n• **Maintenance:** Regular service scheduled\n\n**Check:**\n• **Assets tab** - Detailed HVAC information\n• **Work Orders** - Maintenance tasks";
      } else if (msgLower.includes("electrical") || msgLower.includes("power") || msgLower.includes("electric")) {
        fallbackResponse += "⚡ **Electrical Systems:**\n\n• **Main Electrical Panel** - Ground Floor\n• **Living Room Outlet** - Operational\n• **Kitchen Outlet** - Operational\n• **LED Lighting** - All rooms covered\n\n**View in:**\n• **Assets tab** - Complete electrical inventory";
      } else {
        fallbackResponse += "🤖 **I can help you explore the Sample House!**\n\n**Available Features:**\n• **Graph View** - Component relationships\n• **Assets** - Building systems inventory\n• **Work Orders** - Maintenance management\n• **Dashboard** - Overview and metrics\n\n**Try asking about:**\n• House structure and layout\n• Doors, windows, rooms\n• HVAC, electrical, plumbing systems\n• Work orders and maintenance";
      }
      
      const errorMessage = { 
        role: "assistant", 
        content: fallbackResponse, 
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
          className="h-14 w-14 rounded-full bg-gradient-to-br from-[var(--palantir-text-accent)] to-[#2563eb] hover:from-[#2563eb] hover:to-[#1d4ed8] shadow-lg transition-all duration-200"
        >
          <Bot className="h-6 w-6 text-white" />
        </Button>
      </div>
    );
  }

  return (
    <div className="fixed bottom-6 right-6 z-50 w-96 h-[600px] bg-[var(--palantir-bg-elevated)] border border-[var(--palantir-border-primary)] rounded-xl shadow-2xl backdrop-blur-sm">
      <div className="flex items-center justify-between p-4 border-b border-[var(--palantir-border-primary)]">
        <div className="flex items-center gap-2">
          <Bot className="h-5 w-5 text-blue-600" />
          <h3 className="font-semibold text-[var(--palantir-text-primary)]">AI Assistant</h3>
          <Badge className="bg-[var(--palantir-success)]/20 text-[var(--palantir-success)] border border-[var(--palantir-success)]/30 text-xs font-medium">Always On</Badge>
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
              💡 Try: "Show house structure" or "Find all doors"
            </div>
            <Button 
              onClick={() => handleSendMessage()} 
              disabled={isLoading || !message.trim()}
              className="w-full bg-gradient-to-r from-[var(--palantir-text-accent)] to-[#2563eb] hover:from-[#2563eb] hover:to-[#1d4ed8] text-white font-medium shadow-sm hover:shadow-md transition-all duration-200"
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
    { id: "agents", label: "AI Agents", icon: Bot },
    { id: "graph-view", label: "Semantic Graph", icon: Network },
    { id: "telemetry", label: "Live Telemetry", icon: Activity },
    { id: "enterprise", label: "Enterprise Graph", icon: LinkIcon },
    { id: "assets", label: "Assets", icon: Box },
    { id: "work-orders", label: "Work Orders", icon: Clipboard }
  ];

  return (
    <div className="w-64 bg-[var(--palantir-bg-secondary)] border-r border-[var(--palantir-border-primary)] h-full">
      <div className="p-6 border-b border-[var(--palantir-border-primary)]">
        <div className="flex items-center gap-3">
          <Factory className="h-8 w-8 text-[var(--palantir-text-accent)]" />
          <h1 className="text-xl font-bold text-[var(--palantir-text-primary)]">Gemino</h1>
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
                  "w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-all duration-200",
                  activeTab === item.id
                    ? "bg-[var(--palantir-text-accent)] text-white shadow-sm"
                    : "text-[var(--palantir-text-secondary)] hover:bg-[var(--palantir-hover)] hover:text-[var(--palantir-text-primary)]"
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
    // Load dashboard data with error handling
    const loadDashboardData = async () => {
      try {
        console.log("Loading dashboard data...");
        
        // Load work orders for metrics
        let workOrders = [];
        try {
          const woRes = await fetch(`${API_BASE}/workorders`);
          if (woRes.ok) {
            workOrders = await woRes.json();
            console.log("Work orders loaded:", workOrders.length);
          } else {
            console.warn("Work orders API not available, using mock data");
            workOrders = [
              { id: "WO-001", status: "Open", priority: "High" },
              { id: "WO-002", status: "Done", priority: "Medium" },
              { id: "WO-003", status: "Open", priority: "Critical" }
            ];
          }
        } catch (woError) {
          console.warn("Work orders fetch failed, using mock data:", woError);
          workOrders = [
            { id: "WO-001", status: "Open", priority: "High" },
            { id: "WO-002", status: "Done", priority: "Medium" },
            { id: "WO-003", status: "Open", priority: "Critical" }
          ];
        }
        
        // Load asset count
        let countData = { total: 0 };
        try {
          const countRes = await fetch(`${API_BASE}/count?q=assets`);
          if (countRes.ok) {
            countData = await countRes.json();
            console.log("Asset count loaded:", countData.total);
          } else {
            console.warn("Asset count API not available, using mock data");
            countData = { total: 25 };
          }
        } catch (countError) {
          console.warn("Asset count fetch failed, using mock data:", countError);
          countData = { total: 25 };
        }
        
        setMetrics({
          totalAssets: countData.total || 25,
          activeWorkOrders: workOrders.filter(wo => wo.status === "Open").length,
          criticalAlerts: workOrders.filter(wo => wo.priority === "Critical").length,
          completedTasks: workOrders.filter(wo => wo.status === "Done").length
        });
        
        console.log("Dashboard data loaded successfully");
      } catch (error) {
        console.error("Failed to load dashboard data:", error);
        // Set fallback metrics
        setMetrics({
          totalAssets: 25,
          activeWorkOrders: 3,
          criticalAlerts: 1,
          completedTasks: 1
        });
      }
    };

    loadDashboardData();
  }, []);

  return (
    <div className="flex-1 p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-[var(--palantir-text-primary)] tracking-tight">Digital Twin Platform</h1>
          <p className="text-[var(--palantir-text-secondary)] mt-2 text-sm leading-relaxed">
            AI-native semantically normalized IWMS with enterprise graph integration
          </p>
          <div className="flex gap-2 mt-3">
            <Badge className="bg-[var(--palantir-info)]/20 text-[var(--palantir-info)] border border-[var(--palantir-info)]/30 text-xs font-medium">GraphDB RDF</Badge>
            <Badge className="bg-[var(--palantir-info)]/20 text-[var(--palantir-info)] border border-[var(--palantir-info)]/30 text-xs font-medium">IFC-LD</Badge>
            <Badge className="bg-[var(--palantir-warning)]/20 text-[var(--palantir-warning)] border border-[var(--palantir-warning)]/30 text-xs font-medium">223P/Brick</Badge>
            <Badge className="bg-[var(--palantir-success)]/20 text-[var(--palantir-success)] border border-[var(--palantir-success)]/30 text-xs font-medium">TimescaleDB</Badge>
            <Badge className="bg-[var(--palantir-text-muted)]/20 text-[var(--palantir-text-secondary)] border border-[var(--palantir-border-primary)] text-xs font-medium">SSN/SOSA/QUDT</Badge>
          </div>
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

// === Graph View ===
const GraphView = ({ onAIAction }) => {
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [selectedNode, setSelectedNode] = useState(null);
  const [loading, setLoading] = useState(true);
  const containerRef = useRef(null);
  const [size, setSize] = useState({ width: 0, height: 0 });

  useEffect(() => {
    // Load graph data from GraphDB
    const loadGraphData = async () => {
      setLoading(true);
      try {
        console.log("Loading GraphDB RDF graph data...");
        
        // Try to load from GraphDB API
        try {
          const res = await fetch(`${API_BASE}/graphdb/graph?limit=100&hops=2`);
          if (res.ok) {
            const data = await res.json();
            if (data.nodes && data.nodes.length > 0) {
              const nodes = data.nodes.map(n => ({
                id: n.id,
                name: n.name || n.id.split("/").pop() || n.id.split("#").pop(),
                type: n.type || "Unknown",
                labels: n.labels || []
              }));
              const links = data.edges.map(e => ({
                source: e.source,
                target: e.target,
                type: e.type || "RELATED_TO"
              }));
              setGraphData({ nodes, links });
              console.log(`Loaded ${nodes.length} nodes and ${links.length} links from GraphDB`);
              return;
            }
          }
        } catch (apiError) {
          console.warn("GraphDB API failed, using fallback data:", apiError);
        }
        
        // Fallback: Create demo graph showing semantic layers
        console.log("Using fallback semantic graph data");
        setGraphData({
          nodes: [
            // IFC-LD layer
            { id: "ifc:building", name: "Sample House", type: "IfcBuilding", labels: ["IFC-LD"] },
            { id: "ifc:storey", name: "Ground Floor", type: "IfcBuildingStorey", labels: ["IFC-LD"] },
            { id: "ifc:space", name: "Living Room", type: "IfcSpace", labels: ["IFC-LD"] },
            { id: "ifc:terminal", name: "FT_136276", type: "IfcFlowTerminal", labels: ["IFC-LD"] },
            // 223P layer
            { id: "s223:equipment", name: "FT_136276", type: "TerminalUnit", labels: ["223P"] },
            { id: "s223:zone", name: "Zone_Main", type: "Zone", labels: ["223P"] },
            // Brick layer
            { id: "brick:point1", name: "SAT Sensor", type: "Supply_Air_Temperature_Sensor", labels: ["Brick"] },
            { id: "brick:point2", name: "SAF Sensor", type: "Supply_Air_Flow_Sensor", labels: ["Brick"] },
            // SOSA layer
            { id: "sosa:obs1", name: "SAT Observable", type: "ObservableProperty", labels: ["SOSA"] },
            // QUDT layer
            { id: "qudt:temp", name: "Temperature", type: "QuantityKind", labels: ["QUDT"] },
            // TimescaleDB link
            { id: "ts:ft_136276_sat", name: "ft_136276_sat", type: "TimeseriesReference", labels: ["TimescaleDB"] }
          ],
          links: [
            // IFC to 223P
            { source: "ifc:terminal", target: "s223:equipment", type: "representsIfcElement" },
            // 223P to Brick
            { source: "s223:equipment", target: "brick:point1", type: "hasPoint" },
            { source: "s223:equipment", target: "brick:point2", type: "hasPoint" },
            { source: "s223:equipment", target: "s223:zone", type: "serves" },
            // Brick to SOSA
            { source: "brick:point1", target: "sosa:obs1", type: "a" },
            // SOSA to QUDT
            { source: "sosa:obs1", target: "qudt:temp", type: "hasQuantityKind" },
            // Brick to TimescaleDB
            { source: "brick:point1", target: "ts:ft_136276_sat", type: "hasTimeseriesReference" },
            // IFC spatial
            { source: "ifc:building", target: "ifc:storey", type: "CONTAINS" },
            { source: "ifc:storey", target: "ifc:space", type: "CONTAINS" }
          ]
        });
      } catch (error) {
        console.error("Failed to load graph data:", error);
        setGraphData({ nodes: [], links: [] });
      } finally {
        setLoading(false);
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
    const radius = 6 + Math.log((node.degree || 1) + 1) * 2;
    ctx.beginPath();
    ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI, false);
    
    // Color by semantic layer
    const labels = node.labels || [];
    ctx.fillStyle = labels.includes("IFC-LD") ? "#00d4ff" :
                   labels.includes("223P") ? "#f59e0b" :
                   labels.includes("Brick") ? "#8b5cf6" :
                   labels.includes("SOSA") ? "#34d399" :
                   labels.includes("QUDT") ? "#10b981" :
                   labels.includes("TimescaleDB") ? "#ef4444" :
                   node.type?.includes("IfcBuilding") ? "#00d4ff" :
                   node.type?.includes("IfcBuildingStorey") ? "#8b5cf6" :
                   node.type?.includes("IfcSpace") ? "#34d399" :
                   node.type?.includes("IfcFlow") ? "#f59e0b" :
                   "#e2e8f0";
    
    ctx.fill();
    ctx.font = `${Math.max(11 / scale, 8)}px Inter, system-ui`;
    ctx.fillStyle = "#ffffff";
    const label = node.name?.slice(0, 20) || node.id.slice(0, 8);
    ctx.fillText(label, node.x + radius + 4, node.y + 4);
  }, []);

  return (
    <div className="flex-1 p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-[var(--palantir-text-primary)]">Semantic Graph View</h1>
          <p className="text-[var(--palantir-text-secondary)] mt-2">
            RDF graph from GraphDB: IFC-LD + 223P + Brick + SSN/SOSA + QUDT semantic layers
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
          <CardTitle>RDF Semantic Graph (GraphDB)</CardTitle>
          <p className="text-sm text-[var(--palantir-text-muted)]">
            Multi-ontology graph: IFC-LD (physical) → 223P/Brick (operations) → SSN/SOSA (sensing) → QUDT (units)
          </p>
        </CardHeader>
        <CardContent className="h-full p-0">
          <div ref={containerRef} className="h-full w-full">
            {loading ? (
              <div className="h-full flex items-center justify-center">
                <div className="text-center space-y-2">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[var(--palantir-text-accent)] mx-auto"></div>
                  <p className="text-sm text-[var(--palantir-text-muted)]">Loading GraphDB RDF graph...</p>
                </div>
              </div>
            ) : size.width > 0 && size.height > 0 ? (
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
            ) : (
              <div className="h-full flex items-center justify-center">
                <p className="text-[var(--palantir-text-muted)]">Initializing graph...</p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Semantic Layers Legend */}
      <Card className="palantir-card">
        <CardHeader>
          <CardTitle>Semantic Layers</CardTitle>
          <p className="text-sm text-[var(--palantir-text-muted)]">
            Multi-ontology RDF graph showing semantic normalization
          </p>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-[#00d4ff]"></div>
              <span className="text-[var(--palantir-text-primary)]">IFC-LD (Physical)</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-[#f59e0b]"></div>
              <span className="text-[var(--palantir-text-primary)]">223P (Operations)</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-[#8b5cf6]"></div>
              <span className="text-[var(--palantir-text-primary)]">Brick (Points)</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-[#34d399]"></div>
              <span className="text-[var(--palantir-text-primary)]">SOSA (Sensing)</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-[#10b981]"></div>
              <span className="text-[var(--palantir-text-primary)]">QUDT (Units)</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-[#ef4444]"></div>
              <span className="text-[var(--palantir-text-primary)]">TimescaleDB</span>
            </div>
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
                  <span className="text-[var(--palantir-text-muted)]">ID:</span>
                  <span className="text-[var(--palantir-text-accent)] font-mono text-xs">{selectedNode.id}</span>
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
                  .slice(0, 5)
                  .map((link, index) => (
                    <div key={index} className="flex justify-between">
                      <span className="text-[var(--palantir-text-primary)]">
                        {link.type} → {link.source === selectedNode.id ? 
                          graphData.nodes.find(n => n.id === link.target)?.name : 
                          graphData.nodes.find(n => n.id === link.source)?.name}
                      </span>
                    </div>
                  ))}
                {graphData.links.filter(l => l.source === selectedNode.id || l.target === selectedNode.id).length === 0 && (
                  <p className="text-[var(--palantir-text-muted)]">No relationships found</p>
                )}
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
        console.log("Loading assets...");
        
        // Try to load from API first
        let apiCount = 0;
        try {
          const res = await fetch(`${API_BASE}/count?q=assets`);
          if (res.ok) {
            const data = await res.json();
            apiCount = data.total || 0;
            console.log("Asset count from API:", apiCount);
          }
        } catch (apiError) {
          console.warn("API asset count failed, using mock data:", apiError);
        }
        
        // Create comprehensive mock data for sample house
        const mockAssets = [
          { id: "HVAC-01", name: "HVAC Unit Ground Floor", type: "HVAC", location: "Ground Floor", status: "operational", lastMaintenance: "2025-09-15" },
          { id: "HVAC-02", name: "HVAC Unit First Floor", type: "HVAC", location: "First Floor", status: "operational", lastMaintenance: "2025-09-20" },
          { id: "FIRE-01", name: "Fire Panel Main", type: "Fire Safety", location: "Ground Floor", status: "operational", lastMaintenance: "2025-08-10" },
          { id: "FIRE-02", name: "Smoke Detector Living Room", type: "Fire Safety", location: "Living Room", status: "operational", lastMaintenance: "2025-08-15" },
          { id: "FIRE-03", name: "Smoke Detector Kitchen", type: "Fire Safety", location: "Kitchen", status: "warning", lastMaintenance: "2025-07-20" },
          { id: "LIGHT-01", name: "LED Lighting Living Room", type: "Lighting", location: "Living Room", status: "operational", lastMaintenance: "2025-09-25" },
          { id: "LIGHT-02", name: "LED Lighting Kitchen", type: "Lighting", location: "Kitchen", status: "operational", lastMaintenance: "2025-09-22" },
          { id: "LIGHT-03", name: "LED Lighting Bedroom 1", type: "Lighting", location: "Bedroom 1", status: "operational", lastMaintenance: "2025-09-20" },
          { id: "LIGHT-04", name: "LED Lighting Bedroom 2", type: "Lighting", location: "Bedroom 2", status: "operational", lastMaintenance: "2025-09-18" },
          { id: "LIGHT-05", name: "LED Lighting Bathroom", type: "Lighting", location: "Bathroom", status: "operational", lastMaintenance: "2025-09-15" },
          { id: "ELEC-01", name: "Electrical Panel Main", type: "Electrical", location: "Ground Floor", status: "operational", lastMaintenance: "2025-08-30" },
          { id: "ELEC-02", name: "Outlet Living Room", type: "Electrical", location: "Living Room", status: "operational", lastMaintenance: "2025-08-25" },
          { id: "ELEC-03", name: "Outlet Kitchen", type: "Electrical", location: "Kitchen", status: "operational", lastMaintenance: "2025-08-20" },
          { id: "PLUMB-01", name: "Water Heater", type: "Plumbing", location: "Ground Floor", status: "operational", lastMaintenance: "2025-09-10" },
          { id: "PLUMB-02", name: "Kitchen Faucet", type: "Plumbing", location: "Kitchen", status: "operational", lastMaintenance: "2025-09-05" },
          { id: "PLUMB-03", name: "Bathroom Faucet", type: "Plumbing", location: "Bathroom", status: "warning", lastMaintenance: "2025-07-15" },
          { id: "SEC-01", name: "Security Camera Front", type: "Security", location: "Front Door", status: "operational", lastMaintenance: "2025-09-12" },
          { id: "SEC-02", name: "Security Camera Back", type: "Security", location: "Back Door", status: "operational", lastMaintenance: "2025-09-08" }
        ];
        
        console.log(`Loaded ${mockAssets.length} mock assets`);
        setAssets(mockAssets);
        setFilteredAssets(mockAssets);
      } catch (error) {
        console.error("Failed to load assets:", error);
        // Set empty state on complete failure
        setAssets([]);
        setFilteredAssets([]);
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
        console.log("Loading work orders...");
        
        // Try to load from API first
        let apiWorkOrders = [];
        try {
          const res = await fetch(`${API_BASE}/workorders`);
          if (res.ok) {
            apiWorkOrders = await res.json();
            console.log("Work orders from API:", apiWorkOrders.length);
          }
        } catch (apiError) {
          console.warn("API work orders failed, using mock data:", apiError);
        }
        
        // Use API data if available, otherwise use mock data
        if (apiWorkOrders.length > 0) {
          setWorkOrders(apiWorkOrders);
        } else {
          console.log("Using mock work orders data");
          const mockWorkOrders = [
            { id: "WO-001", title: "HVAC Maintenance - Ground Floor", priority: "High", status: "Open", createdAt: "2025-10-15" },
            { id: "WO-002", title: "Replace Kitchen Faucet", priority: "Medium", status: "In Progress", createdAt: "2025-10-14" },
            { id: "WO-003", title: "Fire Safety Inspection", priority: "Critical", status: "Open", createdAt: "2025-10-13" },
            { id: "WO-004", title: "LED Light Replacement - Living Room", priority: "Low", status: "Done", createdAt: "2025-10-12" },
            { id: "WO-005", title: "Security Camera Check", priority: "Medium", status: "Open", createdAt: "2025-10-11" },
            { id: "WO-006", title: "Electrical Panel Inspection", priority: "High", status: "In Progress", createdAt: "2025-10-10" },
            { id: "WO-007", title: "Bathroom Plumbing Repair", priority: "Medium", status: "Done", createdAt: "2025-10-09" },
            { id: "WO-008", title: "Window Cleaning", priority: "Low", status: "Open", createdAt: "2025-10-08" }
          ];
          setWorkOrders(mockWorkOrders);
        }
      } catch (error) {
        console.error("Failed to load work orders:", error);
        setWorkOrders([]);
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
      case "agents":
        return <AgentDashboard />;
      case "graph-view":
        return <GraphView onAIAction={handleAIAction} />;
      case "telemetry":
        return <TelemetryDashboard />;
      case "enterprise":
        return <EnterpriseView />;
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
            <div>
              <h1 className="text-xl font-semibold">RiG: AI-Driven Semantically Normalized IWMS</h1>
              <p className="text-xs text-[var(--palantir-text-muted)]">
                Digital Twin Platform | IFC-LD + 223P + Brick + SSN/SOSA + QUDT | Enterprise Graph (Workday, Maximo, Office365, Network, Finance)
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Badge className="bg-[var(--palantir-info)]/20 text-[var(--palantir-info)] border border-[var(--palantir-info)]/30">
              <Network className="h-3 w-3 mr-1" />
              GraphDB RDF
            </Badge>
            <Badge className="bg-[var(--palantir-success)]/20 text-[var(--palantir-success)] border border-[var(--palantir-success)]/30">
              <Activity className="h-3 w-3 mr-1" />
              TimescaleDB
            </Badge>
            <Badge className="bg-[var(--palantir-text-accent)] text-black">
              <Bot className="h-3 w-3 mr-1" />
              AI-Powered Digital Twin
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
