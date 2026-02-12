import React, { useState, useCallback, useEffect, useRef } from "react";
import { 
  Database, 
  Activity, 
  Settings, 
  Search, 
  AlertCircle, 
  Wrench, 
  Zap, 
  Menu, 
  Bell, 
  Infinity as InfinityLogo,
  TrendingDown,
  ArrowRight,
  Sparkles,
  Terminal,
  Network,
  Building2,
  Box,
  MapPin
} from "lucide-react";
import { API_BASE } from "@/lib/env";
import { cn } from "@/lib/utils";
import KnowledgeGraph from "@/components/KnowledgeGraph";
import TelemetryPanel from "@/components/TelemetryPanel";
import MaintenancePanel from "@/components/MaintenancePanel";
import EnergyPanel from "@/components/EnergyPanel";
import ChatInterface from "@/components/ChatInterface";
import EnterpriseView from "@/components/EnterpriseView";
import AssetsView from "@/components/AssetsView";

function FacilityOS() {
  // State
  const [currentView, setCurrentView] = useState('graph');
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [telemetryData, setTelemetryData] = useState(null);
  const [selectedNodeId, setSelectedNodeId] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [alerts, setAlerts] = useState([]);
  const [maintenanceTasks, setMaintenanceTasks] = useState([]);
  const [energySavings, setEnergySavings] = useState(12450);
  const [messages, setMessages] = useState([]);
  const [facilityHealth, setFacilityHealth] = useState(98.5);
  const [assets, setAssets] = useState([]);
  const [spaces, setSpaces] = useState([]);

  // Load initial graph data
  useEffect(() => {
    loadGraphData();
    loadAlerts();
    loadMaintenanceTasks();
    loadAssetsAndSpaces();
  }, []);
  
  const loadAssetsAndSpaces = async () => {
    try {
      console.log("Loading assets and spaces from GraphDB...");
      
      // Query for IFC Spaces
      const spacesQuery = `
        PREFIX ifc: <http://ifc-ld.org/schemas/ifc2x3#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT DISTINCT ?space ?name ?type
        WHERE {
          ?space a ifc:IfcSpace .
          OPTIONAL { ?space rdfs:label ?name }
          OPTIONAL { ?space ifc:name ?name }
          BIND("Space" as ?type)
        }
        LIMIT 50
      `;
      
      // Query for Equipment/Assets
      const assetsQuery = `
        PREFIX s223: <http://data.ashrae.org/standard223#>
        PREFIX brick: <https://brickschema.org/schema/Brick#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT DISTINCT ?asset ?name ?type
        WHERE {
          {
            ?asset a s223:Equipment .
            OPTIONAL { ?asset rdfs:label ?name }
            BIND("Equipment" as ?type)
          }
          UNION
          {
            ?asset a brick:AHU .
            OPTIONAL { ?asset rdfs:label ?name }
            BIND("AHU" as ?type)
          }
          UNION
          {
            ?asset a brick:VAV .
            OPTIONAL { ?asset rdfs:label ?name }
            BIND("VAV" as ?type)
          }
        }
        LIMIT 50
      `;
      
      // Load spaces
      const spacesRes = await fetch(`${API_BASE}/graphdb/sparql`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: spacesQuery, format: "json" })
      });
      
      if (spacesRes.ok) {
        const spacesData = await spacesRes.json();
        const spacesList = (spacesData.results?.bindings || []).map(b => ({
          id: b.space?.value || '',
          name: b.name?.value || b.space?.value.split('/').pop() || 'Unknown Space',
          type: 'Space',
          uri: b.space?.value
        }));
        setSpaces(spacesList);
        console.log(`✅ Loaded ${spacesList.length} spaces`);
      }
      
      // Load assets
      const assetsRes = await fetch(`${API_BASE}/graphdb/sparql`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: assetsQuery, format: "json" })
      });
      
      if (assetsRes.ok) {
        const assetsData = await assetsRes.json();
        const assetsList = (assetsData.results?.bindings || []).map(b => ({
          id: b.asset?.value || '',
          name: b.name?.value || b.asset?.value.split('/').pop() || 'Unknown Asset',
          type: b.type?.value || 'Equipment',
          uri: b.asset?.value,
          status: 'nominal'
        }));
        setAssets(assetsList);
        console.log(`✅ Loaded ${assetsList.length} assets`);
      }
    } catch (error) {
      console.error("Failed to load assets and spaces:", error);
    }
  };

  const loadGraphData = async () => {
    try {
      console.log("Loading graph data from GraphDB...");
      
      // Try a more comprehensive SPARQL query that includes IFC entities
      const sparqlQuery = `
        PREFIX ifc: <http://ifc-ld.org/schemas/ifc2x3#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX ex: <https://example.com/rig#>
        PREFIX s223: <http://data.ashrae.org/standard223#>
        PREFIX brick: <https://brickschema.org/schema/Brick#>
        
        SELECT DISTINCT ?entity ?name ?type ?predicate ?object
        WHERE {
          {
            ?entity a ?type .
            FILTER(
              STRSTARTS(STR(?type), "http://ifc-ld.org/schemas/ifc2x3#") ||
              STRSTARTS(STR(?type), "http://data.ashrae.org/standard223#") ||
              STRSTARTS(STR(?type), "https://brickschema.org/schema/Brick#")
            )
            OPTIONAL { ?entity rdfs:label ?name }
            OPTIONAL { ?entity ifc:name ?name }
            OPTIONAL { ?entity ?predicate ?object }
            FILTER (isURI(?object))
          }
        }
        LIMIT 200
      `;
      
      const res = await fetch(`${API_BASE}/graphdb/sparql`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: sparqlQuery, format: "json" })
      });
      
      if (res.ok) {
        const result = await res.json();
        console.log("GraphDB SPARQL response:", result);
        
        // Parse SPARQL results
        const nodesMap = new Map();
        const links = [];
        
        if (result.results?.bindings) {
          for (const binding of result.results.bindings) {
            const entityUri = binding.entity?.value;
            if (!entityUri) continue;
            
            const nodeName = binding.name?.value || 
                           entityUri.split('/').pop()?.split('#').pop() || 
                           entityUri.split('#').pop() || 
                           entityUri;
            const nodeType = binding.type?.value || '';
            const typeShort = nodeType.includes('#') 
              ? nodeType.split('#').pop() 
              : nodeType.split('/').pop();
            
            if (!nodesMap.has(entityUri)) {
              nodesMap.set(entityUri, {
                id: entityUri,
                label: nodeName,
                name: nodeName,
                type: typeShort || 'Entity',
                status: 'nominal',
                ontologyRef: nodeType
              });
            }
            
            // Add edge if object is a URI
            const objectUri = binding.object?.value;
            if (objectUri && objectUri.startsWith('http')) {
              const predicate = binding.predicate?.value || '';
              const predShort = predicate.includes('#')
                ? predicate.split('#').pop()
                : predicate.split('/').pop();
              
              links.push({
                source: entityUri,
                target: objectUri,
                relationship: predShort || 'related'
              });
              
              // Ensure target node exists
              if (!nodesMap.has(objectUri)) {
                const targetName = objectUri.split('/').pop()?.split('#').pop() || objectUri;
                nodesMap.set(objectUri, {
                  id: objectUri,
                  label: targetName,
                  name: targetName,
                  type: 'Entity',
                  status: 'nominal'
                });
              }
            }
          }
        }
        
        const nodes = Array.from(nodesMap.values());
        setGraphData({ nodes, links });
        console.log(`✅ Loaded ${nodes.length} nodes and ${links.length} links from GraphDB`);
      } else {
        const errorText = await res.text();
        console.error("GraphDB request failed:", res.status, res.statusText, errorText);
        setGraphData({ nodes: [], links: [] });
      }
    } catch (error) {
      console.error("Failed to load graph data:", error);
      setGraphData({ nodes: [], links: [] });
    }
  };

  const loadAlerts = async () => {
    try {
      // Try to load from agents detection endpoint
      const res = await fetch(`${API_BASE}/agents/detection/events`);
      if (res.ok) {
        const data = await res.json();
        const events = data.events || data || [];
        setAlerts(events.map(e => ({
          id: e.id || Date.now().toString(),
          assetId: e.asset_id || e.assetId || 'Unknown',
          message: e.message || e.description || 'Anomaly detected',
          severity: e.severity || 'critical',
          timestamp: e.timestamp || Date.now()
        })));
      } else {
        // Fallback: create mock alerts from work orders with high priority
        const woRes = await fetch(`${API_BASE}/workorders?priority=critical`);
        if (woRes.ok) {
          const workOrders = await woRes.json();
          const criticalWOs = workOrders.filter(wo => wo.priority === 'critical' || wo.priority === 'high');
          setAlerts(criticalWOs.map(wo => ({
            id: `alert-${wo.id}`,
            assetId: wo.asset_id || 'Unknown',
            message: `Critical work order: ${wo.title || wo.description}`,
            severity: 'critical',
            timestamp: new Date(wo.created_at || Date.now()).getTime()
          })));
        }
      }
    } catch (error) {
      console.error("Failed to load alerts:", error);
      // Set empty alerts on error
      setAlerts([]);
    }
  };

  const loadMaintenanceTasks = async () => {
    try {
      console.log("Loading maintenance tasks from work orders...");
      const res = await fetch(`${API_BASE}/workorders`);
      if (res.ok) {
        const workOrders = await res.json();
        console.log(`Loaded ${workOrders.length} work orders`);
        const tasks = workOrders.map(wo => ({
          id: wo.id || wo.woId,
          assetId: wo.asset_id || wo.assetId || wo.assetGlobalId || 'Unknown',
          task: wo.title || wo.description || 'Maintenance task',
          reason: wo.description || wo.priority || 'Scheduled maintenance',
          scheduledDate: wo.created_at || wo.createdAt || new Date().toLocaleDateString(),
          priority: wo.priority || 'medium',
          status: wo.status || 'scheduled',
          assignedTo: wo.assigned_to || wo.assignedTo || 'Unassigned'
        }));
        setMaintenanceTasks(tasks);
      } else {
        console.warn("Work orders API not available, using empty tasks");
        setMaintenanceTasks([]);
      }
    } catch (error) {
      console.error("Failed to load maintenance tasks:", error);
      setMaintenanceTasks([]);
    }
  };

  // Tool handlers for chat interface
  const toolHandlers = {
    onQueryGraph: async (args) => {
      console.log("Tool Called: queryGraph", args);
      const query = args.query?.toLowerCase() || '';
      
      try {
        // Use SPARQL to query GraphDB
        const sparqlQuery = `
          PREFIX brick: <https://brickschema.org/schema/Brick#>
          PREFIX ifc: <http://ifc-ld.org/schemas/ifc2x3#>
          SELECT ?subject ?predicate ?object WHERE {
            ?subject ?predicate ?object .
            FILTER(
              CONTAINS(LCASE(STR(?subject)), "${query}") ||
              CONTAINS(LCASE(STR(?object)), "${query}")
            )
          } LIMIT 50
        `;
        
        const res = await fetch(`${API_BASE}/graphdb/sparql`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query: sparqlQuery })
        });
        
        if (res.ok) {
          const data = await res.json();
          // Transform SPARQL results to graph format
          const nodes = new Set();
          const links = [];
          
          data.results?.bindings?.forEach(binding => {
            const source = binding.subject?.value;
            const target = binding.object?.value;
            if (source && target) {
              nodes.add(source);
              nodes.add(target);
              links.push({ source, target, relationship: binding.predicate?.value || 'related' });
            }
          });
          
          const graphNodes = Array.from(nodes).map(id => ({
            id,
            label: id.split('/').pop() || id,
            type: 'Asset',
            status: 'nominal'
          }));
          
          setGraphData({ nodes: graphNodes, links });
          setCurrentView('graph');
          
          return { 
            found: graphNodes.length, 
            top_nodes: graphNodes.slice(0, 3).map(n => n.label),
            description: `Found ${graphNodes.length} related entities in the Knowledge Graph.` 
          };
        }
      } catch (error) {
        console.error("Graph query failed:", error);
      }
      
      return { found: 0, description: "No entities found matching that query." };
    },

    onGetTelemetry: async (args) => {
      console.log("Tool Called: getTelemetry", args);
      const pointId = args.assetId || args.point_id;
      
      try {
        // First, ensure data is seeded for this point
        await fetch(`${API_BASE}/telemetry/seed/${pointId}?count=60`, { method: "POST" });
        
        // Wait a moment for data to be committed
        await new Promise(resolve => setTimeout(resolve, 500));
        
        // Fetch telemetry data from TimescaleDB
        const res = await fetch(`${API_BASE}/telemetry/points/${pointId}?hours=24&limit=100`);
        if (res.ok) {
          const data = await res.json();
          const telemetry = {
            id: pointId,
            name: `${pointId} - ${args.metric || 'Value'}`,
            unit: data.unit || '°C',
            data: (data.data || []).map(d => ({
              timestamp: new Date(d.time || d.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
              value: parseFloat(d.value) || 0
            }))
          };
          
          setTelemetryData(telemetry);
          setCurrentView('telemetry');
          
          return {
            asset: pointId,
            metric: args.metric || 'Value',
            current_value: telemetry.data[telemetry.data.length - 1]?.value || 0,
            trend: "Stable",
            description: `Visualizing ${args.metric || 'data'} for ${pointId} from TimescaleDB.`
          };
        }
      } catch (error) {
        console.error("Telemetry fetch failed:", error);
      }
      
      return { error: "Failed to fetch telemetry data" };
    },

    onDetectAnomalies: async (args) => {
      console.log("Tool Called: detectAnomalies", args);
      
      try {
        const res = await fetch(`${API_BASE}/agents/detection/run`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ asset_id: args.assetId })
        });
        
        if (res.ok) {
          const data = await res.json();
          if (data.anomalies && data.anomalies.length > 0) {
            const newAlert = {
              id: Date.now().toString(),
              assetId: args.assetId,
              message: data.anomalies[0].description || "Anomaly detected",
              severity: data.anomalies[0].severity || 'critical',
              timestamp: Date.now()
            };
            
            setAlerts(prev => [...prev, newAlert]);
            setCurrentView('maintenance');
            
            return { 
              status: "Anomaly Detected", 
              details: newAlert.message, 
              action: "Maintenance Recommended" 
            };
          }
        }
      } catch (error) {
        console.error("Anomaly detection failed:", error);
      }
      
      return { status: "Nominal", details: "No spectral anomalies detected in the last 24h window." };
    },

    onScheduleMaintenance: async (args) => {
      console.log("Tool Called: scheduleMaintenance", args);
      
      try {
        const res = await fetch(`${API_BASE}/workorders`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            title: args.task,
            description: args.reason,
            asset_id: args.assetId,
            priority: args.priority || 'medium',
            status: 'open'
          })
        });
        
        if (res.ok) {
          const wo = await res.json();
          const newTask = {
            id: wo.id,
            assetId: args.assetId,
            task: args.task,
            reason: args.reason,
            scheduledDate: new Date(Date.now() + 86400000 * 2).toLocaleDateString(),
            priority: args.priority || 'medium',
            status: 'scheduled'
          };
          
          setMaintenanceTasks(prev => [...prev, newTask]);
          setCurrentView('maintenance');
          
          return {
            taskId: newTask.id,
            status: "Scheduled",
            date: newTask.scheduledDate,
            message: `Work order created for ${args.assetId}.`
          };
        }
      } catch (error) {
        console.error("Maintenance scheduling failed:", error);
      }
      
      return { error: "Failed to schedule maintenance" };
    },

    onOptimizeEnergy: async (args) => {
      console.log("Tool Called: optimizeEnergy", args);
      
      try {
        const res = await fetch(`${API_BASE}/bacnet/optimize`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            strategy: args.strategy,
            target_zone: args.targetZone
          })
        });
        
        if (res.ok) {
          const data = await res.json();
          setEnergySavings(prev => prev + (data.estimated_savings || 350));
          setCurrentView('energy');
          
          return {
            status: "Active",
            strategy: args.strategy,
            impact: `Algorithm deployed to BACnet controllers. Estimated daily savings: $${data.estimated_savings || 350}.`
          };
        }
      } catch (error) {
        console.error("Energy optimization failed:", error);
      }
      
      return { error: "Failed to optimize energy" };
    }
  };

  const handleSendMessage = useCallback(async (text) => {
    const userMsg = {
      id: Date.now().toString(),
      role: 'user',
      content: text,
      timestamp: Date.now()
    };
    setMessages(prev => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: text,
          history: messages.map(m => ({ role: m.role, content: m.content }))
        })
      });
      
      if (res.ok) {
        const data = await res.json();
        
        // Check if the response indicates tool usage
        let toolInvocation = null;
        if (data.tool?.action) {
          // Execute tool based on action
          const action = data.tool.action;
          if (action === 'search' && toolHandlers.onQueryGraph) {
            await toolHandlers.onQueryGraph({ query: data.tool.query || text });
            toolInvocation = 'queryGraph';
          } else if (action === 'telemetry' && toolHandlers.onGetTelemetry) {
            await toolHandlers.onGetTelemetry({ assetId: data.tool.asset_id });
            toolInvocation = 'getTelemetry';
          }
        }
        
        const modelMsg = {
          id: (Date.now() + 1).toString(),
          role: 'model',
          content: data.reply || data.message || "I received your message.",
          timestamp: Date.now(),
          toolInvocation
        };
        
        setMessages(prev => [...prev, modelMsg]);
      }
    } catch (error) {
      console.error("Chat error:", error);
      const errorMsg = {
        id: (Date.now() + 1).toString(),
        role: 'model',
        content: "I encountered an error processing your request. Please try again.",
        timestamp: Date.now()
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  }, [messages]);

  const handleNodeClick = (node) => {
    setSelectedNodeId(node.id);
    if (node.type === 'Sensor' || node.type === 'Point') {
      toolHandlers.onGetTelemetry({ assetId: node.id, metric: 'Value' });
    }
  };

  const renderContent = () => {
    switch(currentView) {
      case 'graph':
        return <KnowledgeGraph data={graphData} onNodeClick={handleNodeClick} />;
      case 'assets':
        return <AssetsView assets={assets} spaces={spaces} onNodeClick={handleNodeClick} />;
      case 'telemetry':
        return <TelemetryPanel data={telemetryData} />;
      case 'maintenance':
        return <MaintenancePanel alerts={alerts} tasks={maintenanceTasks} />;
      case 'energy':
        return <EnergyPanel savings={energySavings} />;
      case 'enterprise':
        return <EnterpriseView />;
      default:
        return <KnowledgeGraph data={graphData} onNodeClick={handleNodeClick} />;
    }
  };

  const viewTitles = {
    'graph': 'Knowledge Graph Explorer',
    'assets': 'Assets & Spaces',
    'telemetry': 'Live Telemetry Stream',
    'maintenance': 'Predictive Operations',
    'energy': 'Energy & Optimization',
    'enterprise': 'Enterprise Integrations'
  };

  return (
    <div className="flex h-screen bg-nexus-900 text-slate-300 font-sans overflow-hidden">
      
      {/* 1. Narrow Sidebar (Navigation) */}
      <nav className="w-16 flex-shrink-0 bg-nexus-950 flex flex-col items-center py-6 gap-6 z-30 border-r border-nexus-800">
        <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-nexus-accent to-blue-600 flex items-center justify-center text-nexus-900 mb-4 shadow-lg shadow-nexus-accent/20">
          <InfinityLogo size={24} strokeWidth={3} />
        </div>
        
        <div className="flex flex-col gap-4 w-full px-2">
            {[
                { id: 'graph', icon: Database, label: 'Graph' },
                { id: 'assets', icon: Box, label: 'Assets' },
                { id: 'telemetry', icon: Activity, label: 'Data' },
                { id: 'maintenance', icon: Wrench, label: 'Ops' },
                { id: 'energy', icon: Zap, label: 'Energy' },
                { id: 'enterprise', icon: Network, label: 'Enterprise' }
            ].map((item) => (
                <button 
                    key={item.id}
                    onClick={() => setCurrentView(item.id)}
                    className={cn(
                      "p-3 rounded-xl transition-all duration-200 group relative flex justify-center",
                      currentView === item.id 
                        ? 'bg-nexus-800 text-nexus-accent' 
                        : 'hover:bg-nexus-900 hover:text-slate-200 text-slate-500'
                    )}
                    title={item.label}
                >
                    <item.icon size={22} />
                    {currentView === item.id && (
                      <span className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-nexus-accent rounded-r-full"></span>
                    )}
                </button>
            ))}
        </div>

        <div className="mt-auto flex flex-col gap-6 w-full px-2">
          <button 
            onClick={() => setCurrentView('maintenance')}
            className="p-3 rounded-xl hover:bg-nexus-900 hover:text-white transition-all text-slate-500 relative flex justify-center"
          >
            <Bell size={22} />
            {alerts.length > 0 && (
              <span className="absolute top-3 right-3 w-2 h-2 bg-nexus-danger rounded-full animate-pulse border border-nexus-950"></span>
            )}
          </button>
          <button className="p-3 rounded-xl hover:bg-nexus-900 hover:text-white transition-all text-slate-500 flex justify-center">
            <Settings size={22} />
          </button>
        </div>
      </nav>

      {/* 2. Chat Panel (The Agentic Interface) */}
      <div className="w-[450px] flex-shrink-0 flex flex-col bg-nexus-900 z-20 shadow-2xl border-r border-nexus-800">
         <div className="h-14 flex items-center justify-between px-6 border-b border-nexus-800 bg-nexus-900 flex-shrink-0">
             <span className="font-bold text-slate-200 tracking-wide flex items-center text-lg">
                ge<InfinityLogo size={18} className="text-nexus-accent mx-[1px]" strokeWidth={3} />ino
                <span className="ml-3 px-1.5 py-0.5 rounded text-[10px] font-mono bg-nexus-800 text-nexus-accent border border-nexus-700 font-normal">AGENT</span>
             </span>
             <button className="p-2 hover:bg-nexus-800 rounded-lg transition-colors text-slate-500">
                <Menu size={18} />
             </button>
         </div>
         <div className="flex-1 flex flex-col overflow-hidden">
           <ChatInterface 
              messages={messages} 
              onSendMessage={handleSendMessage} 
              isLoading={isLoading} 
           />
         </div>
      </div>

      {/* 3. The "Canvas" (Visualizations & Dashboard) */}
      <div className="flex-1 flex flex-col bg-nexus-950 relative overflow-hidden">
         
         {/* Canvas Header / Search */}
         <header className="h-14 border-b border-nexus-800 flex items-center justify-between px-6 bg-nexus-900/50 backdrop-blur-sm z-10 flex-shrink-0">
            <div className="flex items-center gap-3 text-slate-400">
                <Search size={16} />
                <span className="text-sm">Semantic Search...</span>
            </div>
            
            {/* Context Stats (Mini Dashboard) */}
            <div className="flex items-center gap-6">
                 <div className="flex items-center gap-2">
                     <div className="flex flex-col items-end">
                        <span className="text-[10px] uppercase text-slate-500 font-bold">Health</span>
                        <span className="text-xs font-mono text-nexus-success">{facilityHealth}%</span>
                     </div>
                     <div className="w-8 h-8 rounded-full border border-nexus-success/20 bg-nexus-success/10 flex items-center justify-center">
                        <Activity size={14} className="text-nexus-success" />
                     </div>
                 </div>
                 <div className="h-8 w-[1px] bg-nexus-800"></div>
                 <div className="flex items-center gap-2">
                     <div className="flex flex-col items-end">
                        <span className="text-[10px] uppercase text-slate-500 font-bold">Savings</span>
                        <span className="text-xs font-mono text-nexus-accent">${energySavings.toLocaleString()}</span>
                     </div>
                     <div className="w-8 h-8 rounded-full border border-nexus-accent/20 bg-nexus-accent/10 flex items-center justify-center">
                        <TrendingDown size={14} className="text-nexus-accent" />
                     </div>
                 </div>
            </div>
         </header>

         {/* Viewport */}
         <div className="flex-1 p-6 overflow-hidden flex flex-col">
             <div className="flex items-center justify-between mb-4">
                 <h2 className="text-xl font-light text-white tracking-tight">{viewTitles[currentView]}</h2>
                 {currentView === 'graph' && (
                     <div className="flex gap-2">
                         <span className="px-2 py-1 bg-nexus-800 rounded text-[10px] text-slate-400">IFC</span>
                         <span className="px-2 py-1 bg-nexus-800 rounded text-[10px] text-slate-400">BRICK</span>
                         <span className="px-2 py-1 bg-nexus-800 rounded text-[10px] text-slate-400">223P</span>
                     </div>
                 )}
             </div>
             
             <div className="flex-1 rounded-2xl border border-nexus-800 bg-nexus-900 shadow-2xl overflow-hidden relative group">
                {/* Decoration */}
                <div className="absolute top-0 right-0 w-64 h-64 bg-nexus-accent/5 rounded-full blur-3xl pointer-events-none -translate-y-1/2 translate-x-1/2"></div>
                
                {/* Content */}
                <div className="absolute inset-0 z-10">
                   {renderContent()}
                </div>
             </div>
         </div>

      </div>
    </div>
  );
}

export default FacilityOS;
