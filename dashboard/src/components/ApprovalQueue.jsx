import React from 'react';
import { useAgent } from '../context/AgentContext';
import { AlertCircle, Check, X } from 'lucide-react';

const ApprovalQueue = () => {
  const { approvals, approveChange, rejectChange } = useAgent();

  return (
    <div className="glass-panel rounded-2xl overflow-hidden flex flex-col h-[calc(100vh-8rem)]">
      <div className="p-5 border-b border-slate-800 bg-slate-800/50 flex justify-between items-center">
        <h3 className="font-semibold flex items-center space-x-2">
          <AlertCircle className="text-amber-400" size={18} />
          <span>Action Required</span>
        </h3>
        {approvals.length > 0 && (
          <span className="bg-amber-500 text-white text-xs font-bold w-6 h-6 flex items-center justify-center rounded-full shadow-[0_0_10px_rgba(245,158,11,0.4)]">
            {approvals.length}
          </span>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {approvals.length === 0 ? (
          <div className="text-center py-12">
            <div className="w-16 h-16 rounded-full bg-slate-800/50 flex items-center justify-center mx-auto mb-4 border border-slate-700">
              <Check className="text-slate-500" size={24} />
            </div>
            <p className="text-slate-400 text-sm">You're all caught up!</p>
            <p className="text-slate-500 text-xs mt-1">No pending agent approvals.</p>
          </div>
        ) : (
          approvals.map(approval => (
            <div key={approval.id} className="bg-slate-900/80 rounded-xl border border-slate-700 overflow-hidden shadow-lg shadow-black/20">
              <div className="p-4 border-b border-slate-800">
                <div className="text-xs font-semibold text-cyan-400 mb-1">{approval.task_label}</div>
                <p className="text-sm text-slate-200">{approval.description}</p>
              </div>
              <div className="bg-[#0d1117] p-4 text-xs font-mono overflow-x-auto">
                {approval.diff.split('\n').map((line, i) => (
                  <div key={i} className={`${line.startsWith('-') ? 'text-rose-400 bg-rose-400/10' : line.startsWith('+') ? 'text-emerald-400 bg-emerald-400/10' : 'text-slate-400'} px-2 py-0.5 rounded`}>
                    {line}
                  </div>
                ))}
              </div>
              <div className="p-3 bg-slate-800/30 flex gap-2">
                <button 
                  onClick={() => approveChange(approval.id)}
                  className="flex-1 bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-400 border border-emerald-500/30 py-2 rounded-lg text-sm font-medium transition-colors flex justify-center items-center gap-1"
                >
                  <Check size={16} /> Approve
                </button>
                <button 
                  onClick={() => rejectChange(approval.id)}
                  className="flex-1 bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20 py-2 rounded-lg text-sm font-medium transition-colors flex justify-center items-center gap-1"
                >
                  <X size={16} /> Reject
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default ApprovalQueue;
