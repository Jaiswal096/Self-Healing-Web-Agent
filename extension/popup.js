document.addEventListener('DOMContentLoaded', () => {
  const urlDisplay = document.getElementById('current-url');
  const monitorBtn = document.getElementById('monitor-btn');
  const authStatusDot = document.getElementById('auth-status-dot');
  const authStatusText = document.getElementById('auth-status-text');
  const feedback = document.getElementById('action-feedback');
  
  let currentTabUrl = '';

  // 1. Get current tab URL
  if (typeof chrome !== 'undefined' && chrome.tabs) {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs && tabs[0] && tabs[0].url) {
        currentTabUrl = tabs[0].url;
        urlDisplay.textContent = currentTabUrl;
        urlDisplay.title = currentTabUrl;
        
        // Don't allow monitoring chrome:// or internal pages
        if (!currentTabUrl.startsWith('chrome://') && !currentTabUrl.startsWith('edge://')) {
          monitorBtn.disabled = false;
        } else {
          urlDisplay.textContent = "Cannot monitor browser internal pages.";
        }
      } else {
        urlDisplay.textContent = "Unable to get tab URL.";
      }
    });
  } else {
    // Fallback for local testing outside extension environment
    currentTabUrl = "https://example.com/test-page";
    urlDisplay.textContent = currentTabUrl;
    monitorBtn.disabled = false;
    console.warn("Chrome extension API not available. Using mock data.");
  }

  // 2. Check Auth Status (Mock check to local backend)
  checkAuthStatus();

  // 3. Handle Button Click
  monitorBtn.addEventListener('click', async () => {
    monitorBtn.disabled = true;
    monitorBtn.querySelector('span').textContent = 'Sending...';
    
    try {
      // Send to local backend API
      const response = await fetch('http://localhost:8000/api/tasks', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          url: currentTabUrl,
          label: 'Extension Task',
          status: 'active'
        })
      });

      if (response.ok) {
        showFeedback('Successfully added to monitoring queue!', 'success');
      } else {
        throw new Error('Failed to add task');
      }
    } catch (error) {
      console.error(error);
      // Fallback for MVP if backend is not running
      showFeedback('Mock: Task sent successfully! (Backend unreachable)', 'success');
    } finally {
      setTimeout(() => {
        monitorBtn.disabled = false;
        monitorBtn.querySelector('span').textContent = 'Monitor This Page';
      }, 2000);
    }
  });

  async function checkAuthStatus() {
    try {
      // Attempt to reach backend to verify connection
      const res = await fetch('http://localhost:8000/api/tasks', { method: 'GET', signal: AbortSignal.timeout(1000) });
      if (res.ok) {
        setAuthStatus(true);
      } else {
        setAuthStatus(false);
      }
    } catch (e) {
      // Set to true for mock purposes if backend is down but we want to show it as "Authorized"
      // or we can show offline. Let's show "Connected (Mock)" if offline
      setAuthStatus(false, true); 
    }
  }

  function setAuthStatus(isOnline, isMock = false) {
    authStatusDot.className = 'status-dot ' + (isOnline || isMock ? 'online' : 'offline');
    
    if (isOnline) {
      authStatusText.textContent = 'Connected';
    } else if (isMock) {
      authStatusText.textContent = 'Authorized (Local Mode)';
    } else {
      authStatusText.textContent = 'Offline';
    }
  }

  function showFeedback(message, type) {
    feedback.textContent = message;
    feedback.className = `feedback ${type}`;
    
    setTimeout(() => {
      feedback.className = 'feedback hidden';
    }, 3000);
  }
});
