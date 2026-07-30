// background.js - Service worker for Self-Healing Web Agent Monitor

chrome.runtime.onInstalled.addListener(() => {
  console.log('Self-Healing Web Agent Monitor extension installed.');
  
  // Set default configurations
  chrome.storage.local.get(['serverUrl', 'authorized'], (result) => {
    if (!result.serverUrl) {
      chrome.storage.local.set({ serverUrl: 'http://localhost:8000' });
    }
    if (result.authorized === undefined) {
      chrome.storage.local.set({ authorized: false });
    }
  });
});

// Listener for background actions (if needed by content scripts in future)
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'ping') {
    sendResponse({ status: 'active' });
  }
  return true; // Keep response channel open for async response
});
