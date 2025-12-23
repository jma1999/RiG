import React from 'react';
import { AlertTriangle, Calendar, CheckCircle, Wrench, Clock, AlertOctagon } from 'lucide-react';
import { Alert, MaintenanceTask } from '../types';

interface MaintenancePanelProps {
  alerts: Alert[];
  tasks: MaintenanceTask[];
}

const MaintenancePanel: React.FC<MaintenancePanelProps> = ({ alerts, tasks }) => {
  return (
    <div className="h-full w-full bg-nexus-800 rounded-lg border border-nexus-600 p-6 overflow-y-auto">
      
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
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
                <span className="block text-2xl font-bold text-nexus-accent">{tasks.filter(t => t.status === 'scheduled').length}</span>
                <span className="text-[10px] uppercase text-slate-500 tracking-wider">Scheduled</span>
             </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        {/* Active Alerts Section */}
        <div className="space-y-4">
          <h3 className="text-sm font-mono text-slate-500 uppercase flex items-center gap-2 mb-4">
            <AlertOctagon size={14} /> Active Anomalies
          </h3>
          
          {alerts.length === 0 ? (
            <div className="p-8 border border-dashed border-nexus-600 rounded-lg text-center text-slate-500">
               <CheckCircle size={32} className="mx-auto mb-2 opacity-20 text-nexus-success" />
               <p className="text-sm">System Nominal. No anomalies detected.</p>
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
                          {alert.severity}
                       </span>
                       <span className="text-xs text-slate-500 font-mono">
                          {new Date(alert.timestamp).toLocaleTimeString()}
                       </span>
                    </div>
                    <h4 className="text-white font-medium mb-1">{alert.assetId}</h4>
                    <p className="text-sm text-slate-300">{alert.message}</p>
                 </div>
              </div>
            ))
          )}
        </div>

        {/* Scheduled Tasks Section */}
        <div className="space-y-4">
          <h3 className="text-sm font-mono text-slate-500 uppercase flex items-center gap-2 mb-4">
            <Calendar size={14} /> Scheduled Tasks
          </h3>

          {tasks.length === 0 ? (
             <div className="p-8 border border-dashed border-nexus-600 rounded-lg text-center text-slate-500">
                <Clock size={32} className="mx-auto mb-2 opacity-20" />
                <p className="text-sm">No pending maintenance tasks.</p>
             </div>
          ) : (
            tasks.map(task => (
              <div key={task.id} className="bg-nexus-700 p-4 rounded-lg border border-nexus-600 hover:border-nexus-accent/50 transition-colors">
                 <div className="flex justify-between items-start mb-3">
                    <div>
                       <span className={`inline-block w-2 h-2 rounded-full mr-2 ${task.priority === 'high' ? 'bg-nexus-danger' : task.priority === 'medium' ? 'bg-nexus-warning' : 'bg-blue-400'}`}></span>
                       <span className="text-sm font-mono text-nexus-accent">{task.assetId}</span>
                    </div>
                    <span className="text-xs text-slate-400 bg-nexus-800 px-2 py-1 rounded">
                       {task.scheduledDate}
                    </span>
                 </div>
                 <h4 className="text-white text-sm font-semibold mb-1">{task.task}</h4>
                 <p className="text-xs text-slate-400 italic mb-3">Reason: {task.reason}</p>
                 <div className="flex items-center gap-2 mt-2 pt-2 border-t border-nexus-600/50">
                    <span className="text-[10px] text-slate-500 uppercase tracking-wider">Status: {task.status}</span>
                 </div>
              </div>
            ))
          )}
        </div>

      </div>
    </div>
  );
};

export default MaintenancePanel;