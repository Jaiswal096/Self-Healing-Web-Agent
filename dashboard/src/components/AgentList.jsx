import React from 'react';
import { useAgent } from '../context/AgentContext';
import { Activity, ExternalLink, ShieldAlert, CheckCircle2, RefreshCw } from 'lucide-react';

const AgentList = () => {
  const { tasks, loading } = useAgent();

  if (loading) return <div className="text-slate-400 animate-pulse p-4">Loading tasks...</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold flex items-center space-x-2">
          <Activity className="text-cyan-400" size={20} />
          <span>Active Monitoring Tasks</span>
        </h3>
        <span className="bg-slate-800 text-slate-300 text-xs font-medium px-2.5 py-1 rounded-full border border-slate-700">
          {tasks.length} Total
        </span>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {tasks.map(task => (
          <AgentCard key={task.id} task={task} />
        ))}
        
        {tasks.length === 0 && (
          <div className="col-span-full p-8 border border-dashed border-slate-700 rounded-2xl text-center">
            <p className="text-slate-400">No active monitoring tasks. Add one to get started.</p>
          </div>
        )}
      </div>
    </div>
  );
};

const AgentCard = ({ task }) => {
  const getStatusConfig = (status) => {
    switch (status) {
      case 'active': return { icon: <CheckCircle2 size={16} />, color: 'text-emerald-400', bg: 'bg-emerald-400/10', border: 'border-emerald-400/20', text: 'Monitoring' };
      case 'healing': return { icon: <RefreshCw size={16} className="animate-spin" />, color: 'text-amber-400', bg: 'bg-amber-400/10', border: 'border-amber-400/20', text: 'Healing in Progress' };
      case 'error': return { icon: <ShieldAlert size={16} />, color: 'text-rose-400', bg: 'bg-rose-400/10', border: 'border-rose-400/20', text: 'Broken' };
      default: return { icon: <Activity size={16} />, color: 'text-slate-400', bg: 'bg-slate-400/10', border: 'border-slate-400/20', text: status };
    }
  };

  const config = getStatusConfig(task.status);

  return (
    <div className="glass-panel p-5 hover:border-slate-600/80 transition-colors group">
      <div className="flex justify-between items-start mb-4">
        <div>
          <h4 className="font-semibold text-slate-200 mb-1">{task.label}</h4>
          <a href={task.url} target="_blank" rel="noopener noreferrer" className="text-xs text-slate-400 hover:text-cyan-400 flex items-center space-x-1 truncate max-w-[200px]">
            <span>{task.url}</span>
            <ExternalLink size={12} />
          </a>
        </div>
        <div className={`flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${config.bg} ${config.color} ${config.border}`}>
          {config.icon}
          <span>{config.text}</span>
        </div>
      </div>
      
      <div className="grid grid-cols-2 gap-4 mt-6">
        <div className="bg-slate-900/50 rounded-lg p-3 border border-slate-800">
          <div className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold mb-1">Last Checked</div>
          <div className="text-sm text-slate-300">{task.last_check}</div>
        </div>
        <div className="bg-slate-900/50 rounded-lg p-3 border border-slate-800">
          <div className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold mb-1">Total Heals</div>
          <div className="text-sm font-medium text-slate-300">{task.heal_count}</div>
        </div>
      </div>
    </div>
  );
};

export default AgentList;
