import React from 'react';
import { Zap, TrendingDown, Leaf, Activity } from 'lucide-react';

const ENERGY_DATA = [
  { time: '00:00', baseline: 420, optimized: 380 },
  { time: '04:00', baseline: 380, optimized: 310 },
  { time: '08:00', baseline: 850, optimized: 720 },
  { time: '12:00', baseline: 1200, optimized: 1050 },
  { time: '16:00', baseline: 1100, optimized: 980 },
  { time: '20:00', baseline: 600, optimized: 510 },
  { time: '23:59', baseline: 450, optimized: 400 },
];

const EnergyPanel = ({ savings }) => {
  const maxValue = Math.max(...ENERGY_DATA.flatMap(d => [d.baseline, d.optimized]));
  
  return (
    <div className="h-full w-full bg-nexus-800 rounded-lg border border-nexus-600 p-6 overflow-y-auto">
      
      {/* Header Stats */}
      <div className="flex flex-col md:flex-row md:items-center justify-between mb-8 gap-4">
         <div>
            <h2 className="text-xl font-bold text-white tracking-wide flex items-center gap-3">
               <Zap className="text-nexus-warning" />
               ENERGY OPTIMIZATION
            </h2>
            <p className="text-sm text-slate-400 mt-1 font-mono">
               BACNET CONTROLS & ALGORITHMIC TUNING
            </p>
         </div>
         <div className="bg-nexus-900/80 border border-nexus-success/30 px-6 py-3 rounded-xl flex items-center gap-4 w-fit">
             <div className="p-2 bg-nexus-success/10 rounded-lg">
                 <TrendingDown size={24} className="text-nexus-success" />
             </div>
             <div>
                 <span className="block text-2xl font-bold text-nexus-success">${savings.toLocaleString()}</span>
                 <span className="text-[10px] uppercase text-slate-400 tracking-wider">Est. Annual Savings</span>
             </div>
         </div>
      </div>

      {/* Main Chart */}
      <div className="h-[400px] w-full bg-nexus-900/30 rounded-lg p-4 border border-nexus-700/50 mb-6">
         <h3 className="text-xs font-mono text-slate-500 uppercase mb-4 ml-2">Load Profile Comparison (kW)</h3>
         <div className="h-full relative">
           <svg className="w-full h-full" viewBox="0 0 800 350" preserveAspectRatio="none">
             {/* Grid */}
             {[0, 1, 2, 3, 4].map(i => (
               <line
                 key={i}
                 x1="0"
                 y1={i * 87.5}
                 x2="800"
                 y2={i * 87.5}
                 stroke="#2d2d3a"
                 strokeWidth="1"
                 strokeDasharray="3 3"
               />
             ))}
             {/* Bars */}
             {ENERGY_DATA.map((d, i) => {
               const x = (i / (ENERGY_DATA.length - 1)) * 750 + 25;
               const baselineHeight = (d.baseline / maxValue) * 300;
               const optimizedHeight = (d.optimized / maxValue) * 300;
               const barWidth = 40;
               
               return (
                 <g key={i}>
                   <rect
                     x={x - barWidth - 5}
                     y={350 - baselineHeight}
                     width={barWidth}
                     height={baselineHeight}
                     fill="#3f3f50"
                     rx="4"
                   />
                   <rect
                     x={x + 5}
                     y={350 - optimizedHeight}
                     width={barWidth}
                     height={optimizedHeight}
                     fill="#00ff9d"
                     rx="4"
                   />
                   <text
                     x={x}
                     y={360}
                     textAnchor="middle"
                     fill="#64748b"
                     fontSize="10"
                   >
                     {d.time}
                   </text>
                 </g>
               );
             })}
           </svg>
         </div>
      </div>

      {/* Strategy Log */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pb-4">
          <div className="bg-nexus-700/50 p-4 rounded-lg border border-nexus-600">
             <div className="flex items-center gap-2 mb-2 text-nexus-accent">
                <Activity size={16} />
                <span className="text-xs font-bold uppercase">Trim & Respond</span>
             </div>
             <p className="text-xs text-slate-300 leading-relaxed min-h-[40px]">
                Dynamically adjusting static pressure setpoints based on VAV damper positions.
             </p>
             <div className="mt-3 pt-3 border-t border-nexus-600/30 text-[10px] text-slate-500 font-mono">Status: ACTIVE • Zone-East</div>
          </div>
          <div className="bg-nexus-700/50 p-4 rounded-lg border border-nexus-600">
             <div className="flex items-center gap-2 mb-2 text-nexus-warning">
                <Leaf size={16} />
                <span className="text-xs font-bold uppercase">Optimal Start</span>
             </div>
             <p className="text-xs text-slate-300 leading-relaxed min-h-[40px]">
                Learning building thermal mass to delay AHU start times without compromising comfort.
             </p>
             <div className="mt-3 pt-3 border-t border-nexus-600/30 text-[10px] text-slate-500 font-mono">Status: SCHEDULED • 05:30 AM</div>
          </div>
          <div className="bg-nexus-700/50 p-4 rounded-lg border border-nexus-600 flex flex-col justify-center items-center text-center">
             <span className="text-3xl font-bold text-white mb-1">12.4%</span>
             <span className="text-xs text-slate-400 uppercase">Load Reduction</span>
             <div className="w-16 h-1 bg-nexus-600 rounded-full mt-2 overflow-hidden">
                <div className="w-2/3 h-full bg-nexus-success"></div>
             </div>
          </div>
      </div>

    </div>
  );
};

export default EnergyPanel;

