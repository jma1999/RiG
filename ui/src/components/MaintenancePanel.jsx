import React, { useState } from 'react';
import { AlertTriangle, Calendar, CheckCircle, Wrench, Clock, AlertOctagon, User, Tag } from 'lucide-react';

const MaintenancePanel = ({ alerts, tasks }) => {
  const [selectedTab, setSelectedTab] = useState('anomalies'); // 'anomalies' or 'tasks'
  return (
    <div className="h-full w-full bg-nexus-800 rounded-lg border border-nexus-600 p-6 overflow-y-auto">
      
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold text-white tracking-wide flex items-center gap-3">
            <Wrench className="text-nexus-accent" />
            PREDICTIVE MAINTENANCE OPS
          </h2>
          <p className="text-sm text-slate-400 mt-1 font-mono">
             AI-DRIVEN ANOMALY DETECTION & SCHEDULING
          </p>
        </div>
        <div className="flex gap-4">
             <div className="text-right">
                <span className="block text-2xl font-bold text-nexus-danger">{alerts.length}</span>
                <span className="text-[10px] uppercase text-slate-500 tracking-wider">Active Alerts</span>
             </div>
             <div className="text-right">
                <span className="block text-2xl font-bold text-nexus-accent">{tasks.filter(t => t.status === 'scheduled' || t.status === 'open').length}</span>
                <span className="text-[10px] uppercase text-slate-500 tracking-wider">Scheduled</span>
             </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6 border-b border-nexus-700">
        <button
          onClick={() => setSelectedTab('anomalies')}
          className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 ${
            selectedTab === 'anomalies'
              ? 'border-nexus-danger text-nexus-danger'
              : 'border-transparent text-slate-500 hover:text-slate-300'
          }`}
        >
          <div className="flex items-center gap-2">
            <AlertOctagon size={14} />
            Active Anomalies ({alerts.length})
          </div>
        </button>
        <button
          onClick={() => setSelectedTab('tasks')}
          className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 ${
            selectedTab === 'tasks'
              ? 'border-nexus-accent text-nexus-accent'
              : 'border-transparent text-slate-500 hover:text-slate-300'
          }`}
        >
          <div className="flex items-center gap-2">
            <Calendar size={14} />
            Scheduled Tasks ({tasks.length})
          </div>
        </button>
      </div>

      {/* Content based on selected tab */}
      {selectedTab === 'anomalies' ? (
        <div className="space-y-4">
          {alerts.length === 0 ? (
            <div className="p-8 border border-dashed border-nexus-600 rounded-lg text-center text-slate-500">
               <CheckCircle size={32} className="mx-auto mb-2 opacity-20 text-nexus-success" />
               <p className="text-sm">System Nominal. No anomalies detected.</p>
               <p className="text-xs mt-2 text-slate-600">AI agents are monitoring telemetry streams</p>
            </div>
          ) : (
            alerts.map(alert => (
              <div key={alert.id} className="bg-nexus-900/50 border-l-4 border-nexus-danger p-4 rounded-r-lg shadow-lg relative overflow-hidden group">
                 <div className="absolute top-0 right-0 p-2 opacity-10 group-hover:opacity-20 transition-opacity">
                    <AlertTriangle size={64} />
                 </div>
                 <div className="relative z-10">
                    <div className="flex justify-between items-start mb-2">
                       <span className="bg-nexus-danger/20 text-nexus-danger px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider">
                          {alert.severity || 'critical'}
                       </span>
                       <span className="text-xs text-slate-500 font-mono">
                          {new Date(alert.timestamp).toLocaleTimeString()}
                       </span>
                    </div>
                    <h4 className="text-white font-medium mb-1">{alert.assetId || alert.asset_id}</h4>
                    <p className="text-sm text-slate-300">{alert.message || alert.description}</p>
                 </div>
              </div>
            ))
          )}
        </div>
      ) : (
        <div className="space-y-4">
          {tasks.length === 0 ? (
             <div className="p-8 border border-dashed border-nexus-600 rounded-lg text-center text-slate-500">
                <Clock size={32} className="mx-auto mb-2 opacity-20" />
                <p className="text-sm">No pending maintenance tasks.</p>
                <p className="text-xs mt-2 text-slate-600">Tasks will appear here when scheduled</p>
             </div>
          ) : (
            tasks.map(task => (
              <div key={task.id} className="bg-nexus-700 p-4 rounded-lg border border-nexus-600 hover:border-nexus-accent/50 transition-colors">
                 <div className="flex justify-between items-start mb-3">
                    <div className="flex items-center gap-2">
                       <span className={`inline-block w-2 h-2 rounded-full ${task.priority === 'high' || task.priority === 'critical' ? 'bg-nexus-danger' : task.priority === 'medium' ? 'bg-nexus-warning' : 'bg-blue-400'}`}></span>
                       <span className="text-sm font-mono text-nexus-accent">{task.assetId || task.asset_id}</span>
                    </div>
                    <div className="flex items-center gap-2">
                       <span className="text-xs text-slate-400 bg-nexus-800 px-2 py-1 rounded">
                          {task.scheduledDate || task.created_at || new Date().toLocaleDateString()}
                       </span>
                    </div>
                 </div>
                 <h4 className="text-white text-sm font-semibold mb-1">{task.task || task.title || task.description}</h4>
                 <p className="text-xs text-slate-400 italic mb-3">Reason: {task.reason || task.priority || 'Scheduled maintenance'}</p>
                 <div className="flex items-center justify-between mt-2 pt-2 border-t border-nexus-600/50">
                    <div className="flex items-center gap-3">
                       <span className="text-[10px] text-slate-500 uppercase tracking-wider">Status: {task.status || 'scheduled'}</span>
                       {task.assignedTo && (
                         <div className="flex items-center gap-1 text-[10px] text-slate-500">
                            <User size={12} />
                            <span>{task.assignedTo}</span>
                         </div>
                       )}
                    </div>
                    <span className={`text-[10px] px-2 py-0.5 rounded ${
                      task.priority === 'high' || task.priority === 'critical' 
                        ? 'bg-nexus-danger/20 text-nexus-danger' 
                        : task.priority === 'medium' 
                        ? 'bg-nexus-warning/20 text-nexus-warning' 
                        : 'bg-blue-400/20 text-blue-400'
                    }`}>
                      {task.priority || 'medium'}
                    </span>
                 </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
};

export default MaintenancePanel;

