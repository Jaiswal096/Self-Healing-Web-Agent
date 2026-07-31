import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';

const AgentContext = createContext();

export const useAgent = () => useContext(AgentContext);

const MOCK_TASKS = [
  { id: '1', label: 'E-commerce Price Monitor', url: 'https://example.com/shop', status: 'active', last_check: '2 mins ago', heal_count: 3 },
  { id: '2', label: 'News Headline Scraper', url: 'https://news.example.com', status: 'healing', last_check: 'Just now', heal_count: 1 },
  { id: '3', label: 'Stock Ticker', url: 'https://finance.example.com', status: 'error', last_check: '1 hour ago', heal_count: 0 },
];

const MOCK_APPROVALS = [
  { id: 'a1', task_id: '1', task_label: 'E-commerce Price Monitor', description: 'Selector update from .price to .price_new', diff: '- .price\n+ .price_new', status: 'pending' },
];

export const AgentProvider = ({ children }) => {
  const [tasks, setTasks] = useState([]);
  const [approvals, setApprovals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [connected, setConnected] = useState(false);

  // Fetch data
  const fetchData = async () => {
    try {
      // Attempt to fetch from local backend first
      const tasksRes = await axios.get('http://localhost:8000/api/tasks', { timeout: 2000 });
      const approvalsRes = await axios.get('http://localhost:8000/api/approvals', { timeout: 2000 });
      setTasks(tasksRes.data.tasks || []);
      setApprovals(approvalsRes.data.approvals || []);
      setConnected(true);
    } catch (error) {
      console.warn("Backend not available, using mock data for UI MVP.");
      setTasks(MOCK_TASKS);
      setApprovals(MOCK_APPROVALS);
      setConnected(false);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  const addTask = async (taskData) => {
    try {
      await axios.post('http://localhost:8000/api/tasks', taskData);
      fetchData();
    } catch (e) {
      // Mock mode
      setTasks([...tasks, { id: Math.random().toString(), status: 'active', last_check: 'Just now', heal_count: 0, ...taskData }]);
    }
  };

  const approveChange = async (approvalId) => {
    try {
      await axios.post(`http://localhost:8000/api/approvals/${approvalId}/approve`);
      fetchData();
    } catch (e) {
      setApprovals(approvals.filter(a => a.id !== approvalId));
    }
  };

  const rejectChange = async (approvalId) => {
    try {
      await axios.post(`http://localhost:8000/api/approvals/${approvalId}/reject`);
      fetchData();
    } catch (e) {
      setApprovals(approvals.filter(a => a.id !== approvalId));
    }
  };

  const value = {
    tasks,
    approvals,
    loading,
    connected,
    addTask,
    approveChange,
    rejectChange
  };

  return (
    <AgentContext.Provider value={value}>
      {children}
    </AgentContext.Provider>
  );
};
