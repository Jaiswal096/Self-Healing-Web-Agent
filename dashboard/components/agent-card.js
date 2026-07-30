/**
 * agent-card.js — Renders a task/agent status card for the dashboard grid.
 */

function renderAgentCard(task) {
    const lastRun = task.last_run
        ? new Date(task.last_run).toLocaleString()
        : 'Never';

    const lastData = task.last_result?.data
        ? (typeof task.last_result.data === 'string'
            ? task.last_result.data.substring(0, 50)
            : JSON.stringify(task.last_result.data).substring(0, 50))
        : '—';

    const errorMsg = task.error_message
        ? `<div class="detail-item" style="grid-column: 1 / -1">
               <span class="detail-label">Error</span>
               <span class="detail-value" style="color: var(--color-error)">${escapeHtml(task.error_message).substring(0, 80)}</span>
           </div>`
        : '';

    return `
        <div class="agent-card" data-task-id="${task.id}">
            <div class="agent-card-header">
                <div>
                    <div class="agent-card-title">${escapeHtml(task.task_label)}</div>
                    <div class="agent-card-url" title="${escapeHtml(task.url)}">${escapeHtml(task.url)}</div>
                </div>
                <span class="status-badge ${task.status}">${formatStatus(task.status)}</span>
            </div>

            <div class="agent-card-details">
                <div class="detail-item">
                    <span class="detail-label">Selector</span>
                    <span class="detail-value">${escapeHtml(task.selector)}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Last Run</span>
                    <span class="detail-value">${lastRun}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Interval</span>
                    <span class="detail-value">${formatInterval(task.interval_seconds)}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Healed</span>
                    <span class="detail-value">${task.healed_count || 0}×</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Last Data</span>
                    <span class="detail-value">${escapeHtml(lastData)}</span>
                </div>
                ${errorMsg}
            </div>

            <div class="agent-card-actions">
                <button class="btn btn-ghost btn-sm" data-action="run" data-task-id="${task.id}">
                    ▶ Run Now
                </button>
                <button class="btn btn-ghost btn-sm" data-action="delete" data-task-id="${task.id}" style="color: var(--color-error)">
                    ✕ Delete
                </button>
            </div>
        </div>
    `;
}

// ── Helpers ───────────────────────────────────────────────────────────────── //

function formatStatus(status) {
    const map = {
        idle: 'Idle',
        monitoring: 'Monitoring',
        healing: 'Healing',
        pending_approval: 'Pending',
        error: 'Error',
    };
    return map[status] || status;
}

function formatInterval(seconds) {
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
    return `${(seconds / 3600).toFixed(1)}h`;
}

function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}
