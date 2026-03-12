import { api, apiFetch } from './lib/api.js';
import { API_BASE_URL, MSG, STORAGE_KEYS, FRONTEND_CALLBACK_PATH } from './lib/constants.js';

// In-memory classification cache: gmailId -> classification
const classificationCache = new Map();

// Expose for testing
export { classificationCache };

// Top-level listener: survives service worker restarts in MV3.
// Only intercepts the specific tab opened by startLogin() (stored in
// chrome.storage.local) so it doesn't interfere with the frontend app.
chrome.tabs.onUpdated.addListener((tabId, changeInfo) => {
  if (!changeInfo.url) return;

  // Check asynchronously whether this tab is the extension's login tab
  chrome.storage.local.get(STORAGE_KEYS.LOGIN_TAB_ID).then((result) => {
    const loginTabId = result[STORAGE_KEYS.LOGIN_TAB_ID];
    if (loginTabId == null || tabId !== loginTabId) return;

    let url;
    try {
      url = new URL(changeInfo.url);
    } catch {
      return;
    }

    if (!url.pathname.endsWith(FRONTEND_CALLBACK_PATH)) return;

    const token = url.searchParams.get('token');
    const error = url.searchParams.get('error');

    if (token || error) {
      // Clean up the login tab marker
      chrome.storage.local.remove(STORAGE_KEYS.LOGIN_TAB_ID);
      chrome.tabs.remove(tabId).catch(() => {});

      if (token) {
        chrome.storage.local.set({ [STORAGE_KEYS.TOKEN]: token });
      }
    }
  });
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  handleMessage(message, sender)
    .then(sendResponse)
    .catch((err) => sendResponse({ error: err.message }));
  return true; // keep channel open for async response
});

export async function handleMessage(message, _sender) {
  switch (message.type) {
    case MSG.GET_AUTH_STATE:
      return getAuthState();
    case MSG.LOGIN:
      return startLogin();
    case MSG.LOGOUT:
      return logout();
    case MSG.GET_EMAILS:
      return getEmails(message.params);
    case MSG.SYNC_EMAILS:
      return syncAndRefresh();
    case MSG.CLASSIFY_EMAILS:
      return classifyAndRefresh();
    case MSG.SUBMIT_FEEDBACK:
      return api.submitFeedback(message.emailId, message.feedback);
    case MSG.GET_CLASSIFICATIONS:
      return getClassificationsForIds(message.gmailIds);
    default:
      return { error: `Unknown message type: ${message.type}` };
  }
}

async function getAuthState() {
  const result = await chrome.storage.local.get(STORAGE_KEYS.TOKEN);
  const token = result[STORAGE_KEYS.TOKEN];
  if (!token) {
    return { authenticated: false };
  }
  try {
    const user = await api.getMe();
    return { authenticated: true, user };
  } catch {
    return { authenticated: false };
  }
}

async function startLogin() {
  // /auth/login is public — use raw fetch, not apiFetch (which requires token for auth header)
  const baseUrlResult = await chrome.storage.local.get(STORAGE_KEYS.API_BASE_URL);
  const baseUrl = baseUrlResult[STORAGE_KEYS.API_BASE_URL] || API_BASE_URL;

  const response = await fetch(`${baseUrl}/auth/login`);
  if (!response.ok) {
    throw new Error('Failed to get login URL');
  }
  const { authorization_url } = await response.json();

  // Open the OAuth page in a new tab. The top-level tabs.onUpdated listener
  // will capture the callback token. The popup will close when this tab opens
  // (standard Chrome behavior), so we return immediately.
  // Persist the tab ID so the listener (and service worker restarts) know
  // which tab to intercept — avoids hijacking the frontend's own callback.
  const tab = await chrome.tabs.create({ url: authorization_url });
  await chrome.storage.local.set({ [STORAGE_KEYS.LOGIN_TAB_ID]: tab.id });
  return { success: true, pending: true };
}

async function logout() {
  await chrome.storage.local.remove(STORAGE_KEYS.TOKEN);
  classificationCache.clear();
  return { success: true };
}

async function getEmails(params = {}) {
  const data = await api.getEmails(params);
  updateCache(data.emails);
  return data;
}

async function syncAndRefresh() {
  const result = await api.syncEmails();
  // Refresh email list to update cache
  if (result.synced > 0) {
    try {
      const data = await api.getEmails({ page_size: 100 });
      updateCache(data.emails);
    } catch {
      // Non-critical: cache will be stale but that's fine
    }
  }
  return result;
}

async function classifyAndRefresh() {
  const result = await api.classifyEmails();
  // Refresh cache after classification
  try {
    const data = await api.getEmails({ page_size: 100 });
    updateCache(data.emails);
  } catch {
    // Non-critical
  }
  return result;
}

function updateCache(emails) {
  if (!emails) return;
  for (const email of emails) {
    if (email.gmail_id && email.classification) {
      classificationCache.set(email.gmail_id, email.classification);
    }
  }
  notifyContentScripts();
}

async function notifyContentScripts() {
  try {
    const tabs = await chrome.tabs.query({ url: 'https://mail.google.com/*' });
    const cacheObj = Object.fromEntries(classificationCache);
    for (const tab of tabs) {
      chrome.tabs.sendMessage(tab.id, {
        type: MSG.CLASSIFICATIONS_UPDATED,
        cache: cacheObj,
      }).catch(() => {}); // tab might not have content script ready
    }
  } catch {
    // No Gmail tabs open, that's fine
  }
}

function getClassificationsForIds(gmailIds) {
  const results = {};
  if (!gmailIds) return results;
  for (const id of gmailIds) {
    if (classificationCache.has(id)) {
      results[id] = classificationCache.get(id);
    }
  }
  return results;
}
