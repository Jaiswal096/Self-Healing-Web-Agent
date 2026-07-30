/**
 * add-task-form.js — Setup interaction and handlers for the Add Task modal form.
 */

function initAddTaskForm() {
    const modal = document.getElementById('modal-add-task');
    const btnOpen = document.getElementById('btn-add-task');
    const btnClose = document.getElementById('btn-close-add-task');
    const btnCancel = document.getElementById('btn-cancel-add-task');
    const form = document.getElementById('form-add-task');

    if (!modal || !btnOpen || !form) {
        console.error('Add Task Modal elements not found.');
        return;
    }

    // Open modal
    btnOpen.addEventListener('click', () => {
        modal.classList.add('active');
        document.getElementById('input-url').focus();
    });

    // Close modal helper
    const closeModal = () => {
        modal.classList.remove('active');
        form.reset();
    };

    btnClose.addEventListener('click', closeModal);
    btnCancel.addEventListener('click', closeModal);

    // Close on click outside modal
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeModal();
        }
    });

    // Handle form submit
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const url = document.getElementById('input-url').value.trim();
        const selector = document.getElementById('input-selector').value.trim();
        const label = document.getElementById('input-label').value.trim();
        const interval = parseInt(document.getElementById('input-interval').value.trim(), 10) || 300;

        try {
            showToast('Adding monitoring task…', 'info');
            await api.createTask({
                url: url,
                selector: selector,
                task_label: label,
                interval_seconds: interval
            });
            showToast('Task added successfully and monitoring started.', 'success');
            closeModal();
            // Refresh parent dashboard
            if (typeof refresh === 'function') {
                await refresh();
            }
        } catch (err) {
            showToast(`Failed to add task: ${err.message}`, 'error');
        }
    });
}
