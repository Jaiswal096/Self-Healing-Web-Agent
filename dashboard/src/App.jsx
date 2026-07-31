import React, { useState, useEffect } from 'react';
import DashboardLayout from './components/DashboardLayout';
import AgentList from './components/AgentList';
import ApprovalQueue from './components/ApprovalQueue';
import { AgentProvider } from './context/AgentContext';

function App() {
  return (
    <AgentProvider>
      <DashboardLayout>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="col-span-1 lg:col-span-2 space-y-8">
            <AgentList />
          </div>
          <div className="col-span-1">
            <ApprovalQueue />
          </div>
        </div>
      </DashboardLayout>
    </AgentProvider>
  );
}

export default App;
