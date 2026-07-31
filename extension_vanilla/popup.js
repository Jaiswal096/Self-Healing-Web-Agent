// popup.js - Interactive behavior for Self-Healing Web Agent Monitor extension

document.addEventListener('DOMContentLoaded', async () => {
  // UI Elements
  const activeUrlEl = document.getElementById('active-url');
  const serverUrlInput = document.getElementById('server-url');
  const taskLabelInput = document.getElementById('task-label');
  const selectorInput = document.getElementById('selector');
  const intervalSelect = document.getElementById('interval');
  const registerBtn = document.getElementById('register-task-btn');
  const authBtn = document.getElementById('auth-btn');
  const connectionBadge = document.getElementById('connection-badge');
  const authStatusBadge = document.getElementById('auth-status-badge');
  const openDashboardLnk = document.getElementById('open-dashboard-lnk');

  let activeTabUrl = '';
  let activeTabTitle = '';

  // 1. Detect environment and get active tab URL
  if (typeof chrome !== 'undefined' && chrome.tabs) {
    // True Extension Environment
    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (tab && tab.url) {
        activeTabUrl = tab.url;
        activeTabTitle = tab.title || '';
        
        // Populate inputs if URL looks like an e-commerce page or books.toscrape.com
        activeUrlEl.textContent = activeTabUrl;
        
        // Auto-generate a simple task label
        if (activeTabUrl.includes('books.toscrape.com')) {
          taskLabelInput.value = 'book_price';
          selectorInput.value = '.price_color';
        } else {
          // Clean task label from host
          try {
            const domain = new URL(activeTabUrl).hostname.replace('www.', '').split('.')[0];
            taskLabelInput.value = `${domain}_price`;
            selectorInput.value = '.price'; // default guess
          } catch (e) {
            taskLabelInput.value = 'web_task';
          }
        }
      }
    } catch (err) {
      console.error('Error fetching tab info:', err);
      activeUrlEl.textContent = 'Error fetching URL';
    }
  } else {
    // Web Preview / Non-Extension Mode
    activeTabUrl = 'https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html';
    activeTabTitle = 'A Light in the Attic | Books to Scrape';
    activeUrlEl.textContent = activeTabUrl;
    taskLabelInput.value = 'book_price';
    selectorInput.value = '.price_color';
  }

  // 2. Load stored settings (Server URL & Auth State)
  if (typeof chrome !== 'undefined' && chrome.storage && chrome.storage.local) {
    chrome.storage.local.get(['serverUrl', 'authorized'], (data) => {
      if (data.serverUrl) {
        serverUrlInput.value = data.serverUrl;
      }
      if (data.authorized) {
        setAuthStatus(true);
      } else {
        setAuthStatus(false);
      }
      checkServerStatus();
    });
  } else {
    // Fallback for local testing
    const storedServer = localStorage.getItem('agent_server_url');
    if (storedServer) serverUrlInput.value = storedServer;
    const isAuth = localStorage.getItem('agent_authorized') === 'true';
    setAuthStatus(isAuth);
    checkServerStatus();
  }

  // 3. Status helpers
  function setAuthStatus(isAuthorized) {
    if (isAuthorized) {
      authStatusBadge.textContent = 'Authorized';
      authStatusBadge.className = 'badge badge-authorized';
      authBtn.textContent = 'Revoke Authorization';
      authBtn.classList.remove('btn-secondary');
      authBtn.classList.add('btn-secondary'); // keep styled, or could style differently
      registerBtn.disabled = !isServerConnected();
    } else {
      authStatusBadge.textContent = 'Unauthorized';
      authStatusBadge.className = 'badge badge-unauthorized';
      authBtn.textContent = 'Request Connection Authorization';
      authBtn.classList.remove('btn-secondary');
      authBtn.classList.add('btn-primary');
      registerBtn.disabled = true;
    }
  }

  function isServerConnected() {
    return connectionBadge.classList.contains('badge-connected');
  }

  // 4. Ping server status
  async function checkServerStatus() {
    const serverUrl = serverUrlInput.value.trim() || 'http://localhost:8000';
    
    // Save to storage
    if (typeof chrome !== 'undefined' && chrome.storage && chrome.storage.local) {
      chrome.storage.local.set({ serverUrl });
    } else {
      localStorage.setItem('agent_server_url', serverUrl);
    }

    try {
      const response = await fetch(`${serverUrl}/api/status`, {
        method: 'GET',
        headers: { 'Accept': 'application/json' }
      });
      if (response.ok) {
        connectionBadge.textContent = 'Connected';
        connectionBadge.className = 'badge badge-connected';
        
        // If authorized, enable register button
        const isAuth = (authStatusBadge.textContent === 'Authorized');
        registerBtn.disabled = !isAuth;
      } else {
        throw new Error('Not OK');
      }
    } catch (err) {
      connectionBadge.textContent = 'Offline';
      connectionBadge.className = 'badge badge-disconnected';
      registerBtn.disabled = true;
    }
  }

  // Server input change triggers a status check
  serverUrlInput.addEventListener('change', checkServerStatus);
  serverUrlInput.addEventListener('keyup', (e) => {
    if (e.key === 'Enter') checkServerStatus();
  });

  // 5. Connect/Auth Button Handler
  authBtn.addEventListener('click', () => {
    const currentAuth = authStatusBadge.textContent === 'Authorized';
    const nextAuth = !currentAuth;

    if (typeof chrome !== 'undefined' && chrome.storage && chrome.storage.local) {
      chrome.storage.local.set({ authorized: nextAuth }, () => {
        setAuthStatus(nextAuth);
      });
    } else {
      localStorage.setItem('agent_authorized', nextAuth);
      setAuthStatus(nextAuth);
    }
  });

  // 6. Register Task Button Handler
  registerBtn.addEventListener('click', async () => {
    const serverUrl = serverUrlInput.value.trim() || 'http://localhost:8000';
    const taskLabel = taskLabelInput.value.trim();
    const selector = selectorInput.value.trim();
    const intervalSeconds = parseInt(intervalSelect.value, 10);

    if (!taskLabel || !selector) {
      alert('Please fill out both the Task Label and the Target CSS Selector.');
      return;
    }

    registerBtn.disabled = true;
    registerBtn.textContent = 'Registering task...';

    try {
      const response = await fetch(`${serverUrl}/api/tasks`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          url: activeTabUrl,
          selector: selector,
          task_label: taskLabel,
          interval_seconds: intervalSeconds
        })
      });

      if (response.ok) {
        const data = await response.json();
        alert(`Success! Monitoring task registered successfully.\nTask ID: ${data.task.task_id}`);
        
        // Reset button
        registerBtn.textContent = 'Add Page to Monitoring Queue';
        registerBtn.disabled = false;
      } else {
        const errText = await response.text();
        throw new Error(errText || 'Failed to create task');
      }
    } catch (error) {
      console.error(error);
      alert(`Error registering task: ${error.message}`);
      registerBtn.textContent = 'Add Page to Monitoring Queue';
      registerBtn.disabled = false;
    }
  });

  // 7. Navigation link to dashboard
  openDashboardLnk.addEventListener('click', (e) => {
    e.preventDefault();
    const serverUrl = serverUrlInput.value.trim() || 'http://localhost:8000';
    
    if (typeof chrome !== 'undefined' && chrome.tabs) {
      chrome.tabs.create({ url: `${serverUrl}/dashboard/index.html` });
    } else {
      window.open(`${serverUrl}/dashboard/index.html`, '_blank');
    }
  });
});
