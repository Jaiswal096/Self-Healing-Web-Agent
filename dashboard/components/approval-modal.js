/**
 * approval-modal.js — Renders approval cards showing old→new selector diffs
 * and provides approve/reject buttons with confidence bars.
 */

function renderApprovalCard(approval) {
    const confidencePct = Math.round((approval.confidence || 0) * 100);

    return `
        <div class="approval-card" data-approval-id="${approval.id}">
            <div class="approval-card-header">
                <div class="approval-card-title">
                    🔄 Selector Change — ${escapeHtml(approval.task_label)}
                </div>
                <div class="approval-card-subtitle">
                    ${escapeHtml(approval.url)}
                </div>
            </div>

            <div class="selector-diff">
                <div class="diff-old">${escapeHtml(approval.old_selector)}</div>
                <div class="diff-new">${escapeHtml(approval.new_selector)}</div>
            </div>

            <div class="confidence-bar">
                <span class="confidence-bar-label">Confidence</span>
                <div class="confidence-bar-track">
                    <div class="confidence-bar-fill" style="width: ${confidencePct}%"></div>
                </div>
                <span class="confidence-bar-value">${confidencePct}%</span>
            </div>

            ${approval.reasoning ? `
                <div style="margin-bottom: 1rem; font-size: 0.78rem; color: var(--text-secondary); line-height: 1.5;">
                    <strong style="color: var(--text-primary);">Reasoning:</strong> ${escapeHtml(approval.reasoning)}
                </div>
            ` : ''}

            <div class="approval-card-actions">
                <button class="btn btn-success btn-sm" data-action="approve" data-approval-id="${approval.id}">
                    ✓ Approve
                </button>
                <button class="btn btn-danger btn-sm" data-action="reject" data-approval-id="${approval.id}">
                    ✕ Reject
                </button>
            </div>
        </div>
    `;
}
