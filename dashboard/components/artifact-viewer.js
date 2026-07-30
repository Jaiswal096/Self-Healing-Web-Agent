/**
 * artifact-viewer.js — Renders the list of self-healing artifacts and event logs,
 * supporting screenshot inspection and markdown report links.
 */

function renderArtifactList(artifacts) {
    const listContainer = document.getElementById('artifacts-list');
    const emptyState = document.getElementById('artifacts-empty-state');

    if (!listContainer) return;

    if (!artifacts || !artifacts.length) {
        listContainer.innerHTML = '';
        emptyState?.classList.remove('hidden');
        return;
    }

    emptyState?.classList.add('hidden');

    listContainer.innerHTML = artifacts.map(art => {
        const dateStr = art.timestamp 
            ? parseTimestamp(art.timestamp).toLocaleString()
            : 'Unknown time';

        const isPlan = art.type === 'adaptation_plan';
        const isSuccess = art.success === true;
        const apiHost = 'http://localhost:8000';

        // Badge styling
        let badgeClass = 'badge-info';
        let typeLabel = '🩺 Adaptation Plan';
        if (!isPlan) {
            badgeClass = isSuccess ? 'badge-success' : 'badge-error';
            typeLabel = isSuccess ? '✅ Verification Success' : '❌ Verification Failure';
        }

        // Details content
        let detailsHtml = '';
        if (isPlan) {
            const candidatesHtml = (art.candidates || [])
                .map(c => `<li><span class="text-mono">${escapeHtml(c.selector)}</span> (${Math.round(c.confidence * 100)}%)</li>`)
                .join('');

            detailsHtml = `
                <div class="artifact-meta">
                    <span class="meta-label">Failed Selector:</span>
                    <span class="meta-value text-mono text-error">${escapeHtml(art.failed_selector)}</span>
                </div>
                <div class="artifact-meta">
                    <span class="meta-label">AI Reasoning:</span>
                    <span class="meta-value">${escapeHtml(art.reasoning || 'No details.')}</span>
                </div>
                ${candidatesHtml ? `
                <div class="artifact-meta">
                    <span class="meta-label">Proposed Candidates:</span>
                    <ul class="candidates-list">${candidatesHtml}</ul>
                </div>
                ` : ''}
            `;
        } else {
            const sampleData = art.extracted_data
                ? (typeof art.extracted_data === 'string'
                    ? art.extracted_data
                    : JSON.stringify(art.extracted_data))
                : 'None';

            detailsHtml = `
                <div class="artifact-meta">
                    <span class="meta-label">Tested Selector:</span>
                    <span class="meta-value text-mono text-success">${escapeHtml(art.selector)}</span>
                </div>
                <div class="artifact-meta">
                    <span class="meta-label">Data Sample:</span>
                    <span class="meta-value text-mono data-sample-text">${escapeHtml(sampleData)}</span>
                </div>
                ${art.notes ? `
                <div class="artifact-meta">
                    <span class="meta-label">Notes:</span>
                    <span class="meta-value">${escapeHtml(art.notes)}</span>
                </div>
                ` : ''}
            `;
        }

        // Screenshot thumbnail if available
        let screenshotHtml = '';
        if (art.screenshot_path) {
            const webPath = art.screenshot_path.startsWith('http') ? art.screenshot_path : `${apiHost}${art.screenshot_path}`;
            screenshotHtml = `
                <div class="artifact-thumbnail">
                    <img src="${webPath}" alt="Verification Screenshot" class="thumb-img" onclick="openScreenshotModal('${webPath}')">
                    <span class="thumb-hint">🔍 Click to zoom</span>
                </div>
            `;
        }

        // Link to Markdown report served by FastAPI static mount
        const mdFilename = art.filename ? art.filename.replace('.json', '.md') : '';
        const reportLinkHtml = mdFilename
            ? `<a href="${apiHost}/artifacts/${mdFilename}" target="_blank" class="btn btn-ghost btn-sm card-link-btn">
                 📄 View Full Report
               </a>`
            : '';

        return `
            <div class="artifact-card">
                <div class="artifact-card-header">
                    <div>
                        <span class="badge-type ${badgeClass}">${typeLabel}</span>
                        <span class="artifact-time">${dateStr}</span>
                    </div>
                    <div class="artifact-target-url" title="${escapeHtml(art.url)}">
                        URL: ${escapeHtml(art.url)}
                    </div>
                </div>
                <div class="artifact-card-body">
                    <div class="artifact-details-left">
                        <div class="artifact-task-label">Task: <strong>${escapeHtml(art.task_label)}</strong></div>
                        ${detailsHtml}
                    </div>
                    ${screenshotHtml}
                </div>
                <div class="artifact-card-footer">
                    ${reportLinkHtml}
                </div>
            </div>
        `;
    }).join('');
}

// Helper to parse filename timestamps e.g. 20260730_133800
function parseTimestamp(ts) {
    try {
        const year = ts.substring(0, 4);
        const month = parseInt(ts.substring(4, 6), 10) - 1;
        const day = ts.substring(6, 8);
        const hour = ts.substring(9, 11);
        const min = ts.substring(11, 13);
        const sec = ts.substring(13, 15);
        return new Date(Date.UTC(year, month, day, hour, min, sec));
    } catch (e) {
        return new Date();
    }
}

// Lightbox for screenshot magnification
function openScreenshotModal(imgUrl) {
    let overlay = document.getElementById('screenshot-zoom-overlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'screenshot-zoom-overlay';
        overlay.className = 'zoom-overlay';
        overlay.innerHTML = `
            <div class="zoom-container">
                <img id="zoom-img" src="" alt="Zoomed Screenshot">
                <button class="btn-zoom-close" onclick="closeScreenshotModal()">&times;</button>
            </div>
        `;
        document.body.appendChild(overlay);

        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                closeScreenshotModal();
            }
        });
    }

    const zoomImg = document.getElementById('zoom-img');
    if (zoomImg) {
        zoomImg.src = imgUrl;
    }
    overlay.classList.add('active');
}

function closeScreenshotModal() {
    const overlay = document.getElementById('screenshot-zoom-overlay');
    if (overlay) {
        overlay.classList.remove('active');
    }
}
