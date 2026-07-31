import React, { useState } from 'react';
import { X } from 'lucide-react';
import { useAgent } from '../context/AgentContext';

const AddTaskModal = ({ isOpen, onClose }) => {
  const { addTask } = useAgent();
  const [formData, setFormData] = useState({ url: '', label: '', selector: '' });

  if (!isOpen) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    addTask(formData);
    setFormData({ url: '', label: '', selector: '' });
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="glass-panel w-full max-w-md shadow-2xl animate-in zoom-in-95 duration-200">
        <div className="flex justify-between items-center p-5 border-b border-slate-700">
          <h2 className="text-lg font-semibold text-white">Add Monitoring Task</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors">
            <X size={20} />
          </button>
        </div>
        
        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          <div className="space-y-1">
            <label className="text-sm font-medium text-slate-300">Target URL</label>
            <input 
              type="url" 
              required
              placeholder="https://example.com"
              className="w-full bg-slate-900/50 border border-slate-700 rounded-xl px-4 py-2.5 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-all"
              value={formData.url}
              onChange={(e) => setFormData({...formData, url: e.target.value})}
            />
          </div>
          
          <div className="space-y-1">
            <label className="text-sm font-medium text-slate-300">Task Label</label>
            <input 
              type="text" 
              required
              placeholder="e.g. Shopping Cart Price"
              className="w-full bg-slate-900/50 border border-slate-700 rounded-xl px-4 py-2.5 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-all"
              value={formData.label}
              onChange={(e) => setFormData({...formData, label: e.target.value})}
            />
          </div>

          <div className="space-y-1">
            <label className="text-sm font-medium text-slate-300">Target CSS Selector</label>
            <input 
              type="text" 
              required
              placeholder=".product-price > span"
              className="w-full bg-slate-900/50 border border-slate-700 rounded-xl px-4 py-2.5 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-all font-mono text-sm"
              value={formData.selector}
              onChange={(e) => setFormData({...formData, selector: e.target.value})}
            />
          </div>

          <div className="pt-4 flex gap-3">
            <button type="button" onClick={onClose} className="flex-1 btn-secondary">
              Cancel
            </button>
            <button type="submit" className="flex-1 btn-primary">
              Start Monitoring
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default AddTaskModal;
