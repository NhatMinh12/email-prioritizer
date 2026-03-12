import { MSG } from '../lib/constants.js';

const $ = (sel) => document.querySelector(sel);

function showView(viewId) {
  for (const view of ['loading-view', 'login-view', 'main-view']) {
    const el = $(`#${view}`);
    if (el) el.classList.toggle('hidden', view !== viewId);
  }
}

function showStatus(text, isError = false) {
  const el = $('#status-message');
  el.textContent = text;
  el.classList.remove('hidden');
  el.classList.toggle('error', isError);
}

function hideStatus() {
  $('#status-message').classList.add('hidden');
}

function setButtonLoading(btn, loading) {
  btn.disabled = loading;
}

async function loadStats() {
  try {
    const [high, medium, low] = await Promise.all([
      chrome.runtime.sendMessage({ type: MSG.GET_EMAILS, params: { priority: 'high', page_size: 1 } }),
      chrome.runtime.sendMessage({ type: MSG.GET_EMAILS, params: { priority: 'medium', page_size: 1 } }),
      chrome.runtime.sendMessage({ type: MSG.GET_EMAILS, params: { priority: 'low', page_size: 1 } }),
    ]);
    $('#stat-high').textContent = high.total ?? 0;
    $('#stat-medium').textContent = medium.total ?? 0;
    $('#stat-low').textContent = low.total ?? 0;
  } catch (err) {
    showStatus('Failed to load stats', true);
  }
}

async function init() {
  showView('loading-view');

  try {
    const state = await chrome.runtime.sendMessage({ type: MSG.GET_AUTH_STATE });

    if (state.authenticated) {
      $('#user-email').textContent = state.user?.email || '';
      showView('main-view');
      await loadStats();
    } else {
      showView('login-view');
    }
  } catch {
    showView('login-view');
  }
}

// Event listeners
$('#login-btn').addEventListener('click', async () => {
  const btn = $('#login-btn');
  setButtonLoading(btn, true);
  hideStatus();

  try {
    const result = await chrome.runtime.sendMessage({ type: MSG.LOGIN });

    if (result.success) {
      const state = await chrome.runtime.sendMessage({ type: MSG.GET_AUTH_STATE });
      $('#user-email').textContent = state.user?.email || '';
      showView('main-view');
      await loadStats();
    } else {
      showStatus(result.error || 'Login failed', true);
    }
  } catch (err) {
    showStatus(err.message || 'Login failed', true);
  } finally {
    setButtonLoading(btn, false);
  }
});

$('#sync-btn').addEventListener('click', async () => {
  const btn = $('#sync-btn');
  setButtonLoading(btn, true);
  hideStatus();

  try {
    const result = await chrome.runtime.sendMessage({ type: MSG.SYNC_EMAILS });

    if (result.error) {
      showStatus(result.error, true);
    } else {
      showStatus(`Synced ${result.synced ?? 0} emails`);
      await loadStats();
    }
  } catch (err) {
    showStatus(err.message || 'Sync failed', true);
  } finally {
    setButtonLoading(btn, false);
  }
});

$('#classify-btn').addEventListener('click', async () => {
  const btn = $('#classify-btn');
  setButtonLoading(btn, true);
  hideStatus();

  try {
    const result = await chrome.runtime.sendMessage({ type: MSG.CLASSIFY_EMAILS });

    if (result.error) {
      showStatus(result.error, true);
    } else {
      showStatus(result.message || `Classified ${result.classified ?? 0} emails`);
      await loadStats();
    }
  } catch (err) {
    showStatus(err.message || 'Classification failed', true);
  } finally {
    setButtonLoading(btn, false);
  }
});

$('#logout-btn').addEventListener('click', async () => {
  hideStatus();
  await chrome.runtime.sendMessage({ type: MSG.LOGOUT });
  showView('login-view');
});

init();

// Exports for testing
export { init, loadStats, showView, showStatus, hideStatus, setButtonLoading };
