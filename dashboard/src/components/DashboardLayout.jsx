import React, { useState } from 'react';
import { ShieldCheck, Activity, Settings, Bell, LayoutDashboard, Database, Plus } from 'lucide-react';
import { useAgent } from '../context/AgentContext';
import AddTaskModal from './AddTaskModal';

const DashboardLayout = ({ children }) => {
  const { connected } = useAgent();
  const [isModalOpen, setIsModalOpen] = useState(false);

  return (
    <div className="min-h-screen flex bg-agent-dark">
      {/* Sidebar */}
      <aside className="w-64 border-r border-slate-800 flex flex-col glass-panel rounded-none">
        <div className="h-16 flex items-center px-6 border-b border-slate-800">
          <ShieldCheck className="w-8 h-8 text-cyan-400 mr-3" />
          <h1 className="text-lg font-bold bg-clip-text text-transparent bg-gradient-to-r from-cyan-400 to-blue-500 tracking-tight">
            AutoHeal Agent
          </h1>
        </div>
        <nav className="flex-1 py-6 px-4 space-y-2">
          <NavItem icon={<LayoutDashboard size={20} />} label="Dashboard" active />
          <NavItem icon={<Activity size={20} />} label="Activity Logs" />
          <NavItem icon={<Database size={20} />} label="Artifacts" />
          <NavItem icon={<Settings size={20} />} label="Settings" />
        </nav>
        <div className="p-4 border-t border-slate-800">
          <div className="flex items-center space-x-3 px-2 py-2">
            <div className={`w-3 h-3 rounded-full ${connected ? 'bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.5)]' : 'bg-rose-500 shadow-[0_0_10px_rgba(244,63,94,0.5)]'}`}></div>
            <span className="text-sm font-medium text-slate-400">
              {connected ? 'System Online' : 'Local Mock Mode'}
            </span>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col h-screen overflow-hidden">
        {/* Top Navbar */}
        <header className="h-16 border-b border-slate-800 flex items-center justify-between px-8 glass-panel rounded-none z-10">
          <h2 className="text-xl font-semibold text-slate-100">Overview</h2>
          <div className="flex items-center space-x-6">
            <button className="relative text-slate-400 hover:text-cyan-400 transition-colors">
              <Bell size={20} />
              <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-rose-500 rounded-full border-2 border-agent-dark"></span>
            </button>
            <div className="w-px h-6 bg-slate-700"></div>
            <button 
              onClick={() => setIsModalOpen(true)}
              className="btn-primary flex items-center space-x-2 py-1.5 px-4 text-sm"
            >
              <Plus size={16} />
              <span>New Task</span>
            </button>
          </div>
        </header>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto p-8">
          <div className="max-w-7xl mx-auto">
            {children}
          </div>
        </div>
      </main>

      <AddTaskModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} />
    </div>
  );
};

const NavItem = ({ icon, label, active }) => (
  <a href="#" className={`flex items-center space-x-3 px-4 py-3 rounded-xl transition-all duration-200 group ${active ? 'bg-slate-800/80 text-cyan-400 shadow-md shadow-slate-900/20' : 'text-slate-400 hover:bg-slate-800/40 hover:text-slate-200'}`}>
    <div className={`${active ? 'text-cyan-400' : 'text-slate-500 group-hover:text-slate-300'}`}>
      {icon}
    </div>
    <span className="font-medium">{label}</span>
  </a>
);

export default DashboardLayout;
