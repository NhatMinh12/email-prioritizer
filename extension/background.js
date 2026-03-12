import { api, apiFetch } from './lib/api.js';
import { MSG, STORAGE_KEYS, FRONTEND_CALLBACK_PATH } from './lib/constants.js';

// In-memory classification cache: gmailId -> classification
const classificationCache = new Map();

// Expose for testing
export { classificationCache };

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
  const { API_BASE_URL } = await import('./lib/constants.js');
  const baseUrlResult = await chrome.storage.local.get(STORAGE_KEYS.API_BASE_URL);
  const baseUrl = baseUrlResult[STORAGE_KEYS.API_BASE_URL] || API_BASE_URL;

  const response = await fetch(`${baseUrl}/auth/login`);
  if (!response.ok) {
    throw new Error('Failed to get login URL');
  }
  const { authorization_url } = await response.json();

  const tab = await chrome.tabs.create({ url: authorization_url });

  return new Promise((resolve) => {
    const listener = (tabId, changeInfo) => {
      if (tabId !== tab.id || !changeInfo.url) return;

      let url;
      try {
        url = new URL(changeInfo.url);
      } catch {
        return;
      }

      // Check if this is the callback redirect (frontend callback path with token or error)
      if (!url.pathname.endsWith(FRONTEND_CALLBACK_PATH)) return;

      const token = url.searchParams.get('token');
      const error = url.searchParams.get('error');

      if (token || error) {
        chrome.tabs.onUpdated.removeListener(listener);
        chrome.tabs.remove(tabId).catch(() => {});

        if (token) {
          chrome.storage.local.set({ [STORAGE_KEYS.TOKEN]: token }).then(() => {
            resolve({ success: true });
          });
        } else {
          resolve({ error });
        }
      }
    };

    chrome.tabs.onUpdated.addListener(listener);
  });
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
