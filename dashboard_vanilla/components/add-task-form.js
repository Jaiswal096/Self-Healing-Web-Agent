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
        const typeSelect = document.getElementById('input-type');
        const selector = typeSelect.value;
        // Generate a clean task label from the dropdown text (e.g. "Page Title" -> "page_title")
        const rawLabel = typeSelect.options[typeSelect.selectedIndex].text;
        const label = rawLabel.toLowerCase().replace(/[^a-z0-9]/g, '_').replace(/_+/g, '_').replace(/_$/, '');
        const interval = 300; // Default 5 mins

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
