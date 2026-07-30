/**
 * app.js — Core SPA logic for the Self-Healing Web Agent dashboard.
 *
 * Handles API communication, state management, auto-refresh,
 * and orchestrates the UI components.
 */

const API_BASE = 'http://localhost:8000/api';
const REFRESH_INTERVAL = 5000; // 5 seconds

// ── State ────────────────────────────────────────────────────────────────── //

const state = {
    tasks: [],
    approvals: [],
    artifacts: [],
    status: null,
    connected: false,
    refreshTimer: null,
};

// ── API Client ───────────────────────────────────────────────────────────── //

async function apiRequest(path, options = {}) {
    try {
        const response = await fetch(`${API_BASE}${path}`, {
            headers: { 'Content-Type': 'application/json', ...options.headers },
            ...options,
        });
        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            throw new Error(err.detail || `HTTP ${response.status}`);
        }
        return await response.json();
    } catch (err) {
        if (err.message.includes('Failed to fetch') || err.message.includes('NetworkError')) {
            setConnectionStatus('error', 'Disconnected');
            state.connected = false;
        }
        throw err;
    }
}

const api = {
    // Status
    getStatus: () => apiRequest('/status'),

    // Tasks
    listTasks: () => apiRequest('/tasks'),
    createTask: (data) => apiRequest('/tasks', { method: 'POST', body: JSON.stringify(data) }),
    deleteTask: (id) => apiRequest(`/tasks/${id}`, { method: 'DELETE' }),
    runTask: (id) => apiRequest(`/tasks/${id}/run`, { method: 'POST' }),

    // Approvals
    listApprovals: () => apiRequest('/approvals'),
    approveChange: (id) => apiRequest(`/approvals/${id}/approve`, { method: 'POST' }),
    rejectChange: (id) => apiRequest(`/approvals/${id}/reject`, { method: 'POST' }),

    // Artifacts
    listArtifacts: () => apiRequest('/artifacts'),
};

// ── Connection Status ────────────────────────────────────────────────────── //

function setConnectionStatus(type, text) {
    const dot = document.querySelector('#connection-status .status-dot');
    const label = document.querySelector('#connection-status .status-text');
    dot.className = 'status-dot ' + type;
    label.textContent = text;
}

// ── Stats Bar ────────────────────────────────────────────────────────────── //

function updateStats(status) {
    document.getElementById('stat-active-count').textContent = status.total_tasks || 0;
    document.getElementById('stat-pending-count').textContent = status.approvals?.pending || 0;
    document.getElementById('stat-healed-count').textContent = status.total_heals || 0;
    document.getElementById('stat-monitor-status').textContent =
        status.monitor_active ? 'Active' : 'Stopped';
}

// ── Tasks Grid ───────────────────────────────────────────────────────────── //

function renderTasks(tasks) {
    const grid = document.getElementById('tasks-grid');
    const empty = document.getElementById('empty-state');

    if (!tasks.length) {
        grid.innerHTML = '';
        empty.classList.remove('hidden');
        return;
    }

    empty.classList.add('hidden');
    grid.innerHTML = tasks.map(task => renderAgentCard(task)).join('');

    // Bind actions
    grid.querySelectorAll('[data-action="run"]').forEach(btn => {
        btn.addEventListener('click', () => handleRunTask(btn.dataset.taskId));
    });
    grid.querySelectorAll('[data-action="delete"]').forEach(btn => {
        btn.addEventListener('click', () => handleDeleteTask(btn.dataset.taskId));
    });
}

// ── Approvals Section ────────────────────────────────────────────────────── //

function renderApprovals(approvals) {
    const section = document.getElementById('approvals-section');
    const list = document.getElementById('approvals-list');
    const badge = document.getElementById('approval-badge');

    const pending = approvals.filter(a => a.status === 'pending');
    badge.textContent = pending.length;

    if (!pending.length) {
        section.classList.add('hidden');
        return;
    }

    section.classList.remove('hidden');
    list.innerHTML = pending.map(a => renderApprovalCard(a)).join('');

    // Bind actions
    list.querySelectorAll('[data-action="approve"]').forEach(btn => {
        btn.addEventListener('click', () => handleApprove(btn.dataset.approvalId));
    });
    list.querySelectorAll('[data-action="reject"]').forEach(btn => {
        btn.addEventListener('click', () => handleReject(btn.dataset.approvalId));
    });
}

// ── Action Handlers ──────────────────────────────────────────────────────── //

async function handleRunTask(taskId) {
    try {
        showToast('Running task…', 'info');
        await api.runTask(taskId);
        showToast('Task executed successfully.', 'success');
        await refresh();
    } catch (err) {
        showToast(`Run failed: ${err.message}`, 'error');
    }
}

async function handleDeleteTask(taskId) {
    if (!confirm('Delete this monitoring task?')) return;
    try {
        await api.deleteTask(taskId);
        showToast('Task deleted.', 'success');
        await refresh();
    } catch (err) {
        showToast(`Delete failed: ${err.message}`, 'error');
    }
}

async function handleApprove(approvalId) {
    try {
        await api.approveChange(approvalId);
        showToast('✅ Change approved and applied!', 'success');
        await refresh();
    } catch (err) {
        showToast(`Approve failed: ${err.message}`, 'error');
    }
}

async function handleReject(approvalId) {
    try {
        await api.rejectChange(approvalId);
        showToast('Change rejected.', 'warning');
        await refresh();
    } catch (err) {
        showToast(`Reject failed: ${err.message}`, 'error');
    }
}

// ── Toast Notifications ──────────────────────────────────────────────────── //

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('toast-exit');
        toast.addEventListener('animationend', () => toast.remove());
    }, 3500);
}

// ── Main Refresh Loop ────────────────────────────────────────────────────── //

async function refresh() {
    try {
        const [statusRes, tasksRes, approvalsRes, artifactsRes] = await Promise.all([
            api.getStatus(),
            api.listTasks(),
            api.listApprovals(),
            api.listArtifacts(),
        ]);

        state.status = statusRes;
        state.tasks = tasksRes.tasks || [];
        state.approvals = approvalsRes.approvals || [];
        state.artifacts = artifactsRes.artifacts || [];
        state.connected = true;

        setConnectionStatus('connected', 'Connected');
        updateStats(statusRes);
        renderTasks(state.tasks);
        renderApprovals(state.approvals);
        renderArtifactList(state.artifacts);

    } catch (err) {
        // Still show demo state if disconnected
        if (!state.connected) {
            setConnectionStatus('error', 'API Offline');
        }
    }
}

// ── Initialization ───────────────────────────────────────────────────────── //

function init() {
    // Add Task modal
    initAddTaskForm();

    // Refresh button
    document.getElementById('btn-refresh').addEventListener('click', () => {
        refresh();
        showToast('Refreshed!', 'info');
    });

    // Initial fetch + auto-refresh
    refresh();
    state.refreshTimer = setInterval(refresh, REFRESH_INTERVAL);
}

// Boot
document.addEventListener('DOMContentLoaded', init);
