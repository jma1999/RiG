import React, { useState, useCallback } from 'react';
import { Database, Activity, Settings, Search, AlertCircle, Wrench, Zap, Menu, Bell, Infinity as InfinityLogo } from 'lucide-react';
import KnowledgeGraph from './components/KnowledgeGraph';
import TelemetryPanel from './components/TelemetryPanel';
import MaintenancePanel from './components/MaintenancePanel';
import EnergyPanel from './components/EnergyPanel';
import ChatInterface from './components/ChatInterface';
import { geminiService } from './services/geminiService';
import { INITIAL_GRAPH, generateTelemetry } from './constants';
import { AppState, ChatMessage, GraphNode, Alert, MaintenanceTask } from './types';

// Helper for Stats
import { TrendingDown } from 'lucide-react';

function App() {
  // State
  const [state, setState] = useState<AppState>({
    currentView: 'graph',
    graphData: INITIAL_GRAPH,
    telemetryData: null,
    selectedNodeId: null,
    isLoading: false,
    alerts: [],
    maintenanceTasks: [],
    energySavings: 12450 // Initial mock value
  });

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  
  // Handlers for Gemini Tools
  const toolHandlers = {
    onQueryGraph: async (args: { query: string, depth?: number }) => {
      console.log("Tool Called: queryGraph", args);
      const query = args.query.toLowerCase();
      
      const filteredNodes = INITIAL_GRAPH.nodes.filter(n => 
        n.id.toLowerCase().includes(query) || 
        n.label.toLowerCase().includes(query) ||
        n.type.toLowerCase().includes(query)
      );
      
      if (filteredNodes.length > 0) {
        const nodeIds = new Set(filteredNodes.map(n => n.id));
        const relevantLinks = INITIAL_GRAPH.links.filter(l => nodeIds.has(l.source) || nodeIds.has(l.target));
        
        relevantLinks.forEach(l => {
             const source = INITIAL_GRAPH.nodes.find(n => n.id === l.source);
             const target = INITIAL_GRAPH.nodes.find(n => n.id === l.target);
             if(source) nodeIds.add(source.id);
             if(target) nodeIds.add(target.id);
        });

        const expandedNodes = INITIAL_GRAPH.nodes.filter(n => nodeIds.has(n.id));

        setState(prev => ({ 
          ...prev, 
          graphData: { nodes: expandedNodes, links: relevantLinks },
          currentView: 'graph',
          selectedNodeId: filteredNodes[0].id 
        }));
        
        return { 
          found: expandedNodes.length, 
          top_nodes: expandedNodes.slice(0, 3).map(n => n.label),
          description: `Found ${expandedNodes.length} related entities in the Knowledge Graph.` 
        };
      }
      
      return { found: 0, description: "No entities found matching that query." };
    },

    onGetTelemetry: async (args: { assetId: string, metric: string }) => {
      console.log("Tool Called: getTelemetry", args);
      const telemetry = generateTelemetry(args.assetId, args.metric);
      
      setState(prev => ({
        ...prev,
        telemetryData: telemetry,
        currentView: 'telemetry'
      }));

      return {
        asset: args.assetId,
        metric: args.metric,
        current_value: telemetry.data[telemetry.data.length - 1].value,
        trend: "Stable",
        description: `Visualizing ${args.metric} for ${args.assetId}.`
      };
    },

    onDetectAnomalies: async (args: { assetId: string }) => {
      console.log("Tool Called: detectAnomalies", args);
      
      // Simulation: 50/50 chance of finding an anomaly if it's one of the "warning" nodes
      const node = INITIAL_GRAPH.nodes.find(n => n.id === args.assetId);
      const isWarning = node?.status === 'warning';
      
      if (isWarning) {
        const newAlert: Alert = {
          id: Date.now().toString(),
          assetId: args.assetId,
          message: `Spectral analysis detected abnormal vibration patterns (Severity: High).`,
          severity: 'critical',
          timestamp: Date.now()
        };
        
        setState(prev => ({
          ...prev,
          alerts: [...prev.alerts, newAlert],
          currentView: 'maintenance'
        }));
        
        return { 
          status: "Anomaly Detected", 
          details: newAlert.message, 
          action: "Maintenance Recommended" 
        };
      }
      
      return { status: "Nominal", details: "No spectral anomalies detected in the last 24h window." };
    },

    onScheduleMaintenance: async (args: { assetId: string, task: string, reason: string, priority?: 'high' | 'medium' | 'low' }) => {
      console.log("Tool Called: scheduleMaintenance", args);
      
      const newTask: MaintenanceTask = {
        id: Date.now().toString(),
        assetId: args.assetId,
        task: args.task,
        reason: args.reason,
        scheduledDate: new Date(Date.now() + 86400000 * 2).toLocaleDateString(), // +2 days
        priority: args.priority || 'medium',
        status: 'scheduled'
      };

      setState(prev => ({
        ...prev,
        maintenanceTasks: [...prev.maintenanceTasks, newTask],
        currentView: 'maintenance'
      }));

      return {
        taskId: newTask.id,
        status: "Scheduled",
        date: newTask.scheduledDate,
        message: `Work order created for ${args.assetId}.`
      };
    },

    onOptimizeEnergy: async (args: { strategy: string, targetZone?: string }) => {
      console.log("Tool Called: optimizeEnergy", args);
      
      // Simulate savings increase
      setState(prev => ({
        ...prev,
        energySavings: prev.energySavings + 350,
        currentView: 'energy'
      }));

      return {
        status: "Active",
        strategy: args.strategy,
        impact: "Algorithm deployed to BACnet controllers. Estimated daily savings: $350."
      };
    }
  };

  const handleSendMessage = useCallback(async (text: string) => {
    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: text,
      timestamp: Date.now()
    };
    setMessages(prev => [...prev, userMsg]);
    setState(prev => ({ ...prev, isLoading: true }));

    const history = messages.map(m => ({
      role: m.role as 'user' | 'model',
      parts: [{ text: m.content }]
    }));

    const response = await geminiService.sendMessage(history, text, toolHandlers);

    const modelMsg: ChatMessage = {
      id: (Date.now() + 1).toString(),
      role: 'model',
      content: response.text,
      timestamp: Date.now(),
      toolInvocation: response.toolCalls.length > 0 ? response.toolCalls.join(', ') : undefined
    };

    setMessages(prev => [...prev, modelMsg]);
    setState(prev => ({ ...prev, isLoading: false }));

  }, [messages, state]);

  const handleNodeClick = (node: GraphNode) => {
    setState(prev => ({ ...prev, selectedNodeId: node.id }));
    if (node.type === 'Sensor') {
      const telemetry = generateTelemetry(node.id, 'Value');
      setState(prev => ({ ...prev, telemetryData: telemetry, currentView: 'telemetry' }));
    }
  };

  const renderContent = () => {
    switch(state.currentView) {
      case 'graph':
        return <KnowledgeGraph data={state.graphData} onNodeClick={handleNodeClick} />;
      case 'telemetry':
        return <TelemetryPanel data={state.telemetryData} />;
      case 'maintenance':
        return <MaintenancePanel alerts={state.alerts} tasks={state.maintenanceTasks} />;
      case 'energy':
        return <EnergyPanel savings={state.energySavings} />;
      default:
        return <KnowledgeGraph data={state.graphData} onNodeClick={handleNodeClick} />;
    }
  };

  // Maps view mode to human readable title
  const viewTitles: Record<string, string> = {
      'graph': 'Knowledge Graph Explorer',
      'telemetry': 'Live Telemetry Stream',
      'maintenance': 'Predictive Operations',
      'energy': 'Energy & Optimization'
  };

  return (
    <div className="flex h-screen bg-nexus-900 text-slate-300 font-sans selection:bg-nexus-accent selection:text-nexus-900 overflow-hidden">
      
      {/* 1. Narrow Sidebar (Navigation) */}
      <nav className="w-16 flex-shrink-0 bg-nexus-950 border-r border-nexus-800 flex flex-col items-center py-6 gap-6 z-30">
        <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-nexus-accent to-blue-600 flex items-center justify-center text-nexus-900 mb-4 shadow-lg shadow-nexus-accent/20">
          <InfinityLogo size={24} strokeWidth={3} />
        </div>
        
        <div className="flex flex-col gap-4 w-full px-2">
            {[
                { id: 'graph', icon: Database, label: 'Graph' },
                { id: 'telemetry', icon: Activity, label: 'Data' },
                { id: 'maintenance', icon: Wrench, label: 'Ops' },
                { id: 'energy', icon: Zap, label: 'Energy' }
            ].map((item) => (
                <button 
                    key={item.id}
                    onClick={() => setState(p => ({ ...p, currentView: item.id as any }))}
                    className={`p-3 rounded-xl transition-all duration-200 group relative flex justify-center ${state.currentView === item.id ? 'bg-nexus-800 text-nexus-accent' : 'hover:bg-nexus-900 hover:text-slate-200 text-slate-500'}`}
                    title={item.label}
                >
                    <item.icon size={22} />
                    {state.currentView === item.id && <span className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-nexus-accent rounded-r-full"></span>}
                </button>
            ))}
        </div>

        <div className="mt-auto flex flex-col gap-6 w-full px-2">
          <button 
            onClick={() => setState(p => ({ ...p, currentView: 'maintenance' }))}
            className="p-3 rounded-xl hover:bg-nexus-900 hover:text-white transition-all text-slate-500 relative flex justify-center"
          >
            <Bell size={22} />
            {state.alerts.length > 0 && <span className="absolute top-3 right-3 w-2 h-2 bg-nexus-danger rounded-full animate-pulse border border-nexus-950"></span>}
          </button>
          <button className="p-3 rounded-xl hover:bg-nexus-900 hover:text-white transition-all text-slate-500 flex justify-center">
            <Settings size={22} />
          </button>
        </div>
      </nav>

      {/* 2. Chat Panel (The Agentic Interface) */}
      <div className="w-[450px] flex-shrink-0 flex flex-col border-r border-nexus-800 bg-nexus-900 z-20 shadow-2xl">
         <div className="h-14 flex items-center justify-between px-6 border-b border-nexus-800 bg-nexus-900">
             <span className="font-bold text-slate-200 tracking-wide flex items-center text-lg">
                ge<InfinityLogo size={18} className="text-nexus-accent mx-[1px]" strokeWidth={3} />ino
                <span className="ml-3 px-1.5 py-0.5 rounded text-[10px] font-mono bg-nexus-800 text-nexus-accent border border-nexus-700 font-normal">AGENT</span>
             </span>
             <button className="p-2 hover:bg-nexus-800 rounded-lg transition-colors text-slate-500">
                <Menu size={18} />
             </button>
         </div>
         <ChatInterface 
            messages={messages} 
            onSendMessage={handleSendMessage} 
            isLoading={state.isLoading} 
         />
      </div>

      {/* 3. The "Canvas" (Visualizations & Dashboard) */}
      <div className="flex-1 flex flex-col bg-nexus-950 relative overflow-hidden">
         
         {/* Canvas Header / Search */}
         <header className="h-14 border-b border-nexus-800 flex items-center justify-between px-6 bg-nexus-900/50 backdrop-blur-sm z-10">
            <div className="flex items-center gap-3 text-slate-400">
                <Search size={16} />
                <span className="text-sm">Semantic Search...</span>
            </div>
            
            {/* Context Stats (Mini Dashboard) */}
            <div className="flex items-center gap-6">
                 <div className="flex items-center gap-2">
                     <div className="flex flex-col items-end">
                        <span className="text-[10px] uppercase text-slate-500 font-bold">Health</span>
                        <span className="text-xs font-mono text-nexus-success">98.5%</span>
                     </div>
                     <div className="w-8 h-8 rounded-full border border-nexus-success/20 bg-nexus-success/10 flex items-center justify-center">
                        <Activity size={14} className="text-nexus-success" />
                     </div>
                 </div>
                 <div className="h-8 w-[1px] bg-nexus-800"></div>
                 <div className="flex items-center gap-2">
                     <div className="flex flex-col items-end">
                        <span className="text-[10px] uppercase text-slate-500 font-bold">Savings</span>
                        <span className="text-xs font-mono text-nexus-accent">${state.energySavings.toLocaleString()}</span>
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
                 <h2 className="text-xl font-light text-white tracking-tight">{viewTitles[state.currentView]}</h2>
                 {state.currentView === 'graph' && (
                     <div className="flex gap-2">
                         <span className="px-2 py-1 bg-nexus-800 rounded text-[10px] text-slate-400">IFC</span>
                         <span className="px-2 py-1 bg-nexus-800 rounded text-[10px] text-slate-400">BRICK</span>
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

export default App;