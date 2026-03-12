import { describe, it, expect, vi, beforeEach } from 'vitest';
import { JSDOM } from 'jsdom';
import { MSG } from '../lib/constants.js';

// Build popup DOM before each test
function buildPopupDOM() {
  const html = `
    <div id="app">
      <div id="loading-view"></div>
      <div id="login-view" class="hidden">
        <button id="login-btn">Sign in with Google</button>
      </div>
      <div id="main-view" class="hidden">
        <header>
          <span id="user-email"></span>
          <button id="logout-btn">Sign out</button>
        </header>
        <div id="stats">
          <span id="stat-high">-</span>
          <span id="stat-medium">-</span>
          <span id="stat-low">-</span>
        </div>
        <button id="sync-btn">Sync Inbox</button>
        <button id="classify-btn">Classify</button>
        <div id="status-message" class="hidden"></div>
      </div>
    </div>
  `;
  document.body.innerHTML = html;
}

beforeEach(() => {
  resetChromeMocks();
  buildPopupDOM();
});

// We test the popup logic by importing the exported functions
// and simulating chrome.runtime.sendMessage responses

describe('popup views', () => {
  it('shows login view when not authenticated', async () => {
    chrome.runtime.sendMessage.mockResolvedValue({ authenticated: false });

    const { init } = await import('../popup/popup.js');
    await init();

    expect(document.querySelector('#login-view').classList.contains('hidden')).toBe(false);
    expect(document.querySelector('#main-view').classList.contains('hidden')).toBe(true);
  });

  it('shows main view with user email when authenticated', async () => {
    chrome.runtime.sendMessage.mockImplementation((msg) => {
      if (msg.type === MSG.GET_AUTH_STATE) {
        return Promise.resolve({ authenticated: true, user: { email: 'user@test.com' } });
      }
      // Stats calls
      return Promise.resolve({ total: 0, emails: [] });
    });

    const { init } = await import('../popup/popup.js');
    await init();

    expect(document.querySelector('#main-view').classList.contains('hidden')).toBe(false);
    expect(document.querySelector('#login-view').classList.contains('hidden')).toBe(true);
    expect(document.querySelector('#user-email').textContent).toBe('user@test.com');
  });

  it('shows login view when auth check throws', async () => {
    chrome.runtime.sendMessage.mockRejectedValue(new Error('disconnected'));

    const { init } = await import('../popup/popup.js');
    await init();

    expect(document.querySelector('#login-view').classList.contains('hidden')).toBe(false);
  });
});

describe('showView', () => {
  it('toggles visibility of views', async () => {
    const { showView } = await import('../popup/popup.js');

    showView('main-view');
    expect(document.querySelector('#main-view').classList.contains('hidden')).toBe(false);
    expect(document.querySelector('#login-view').classList.contains('hidden')).toBe(true);
    expect(document.querySelector('#loading-view').classList.contains('hidden')).toBe(true);

    showView('login-view');
    expect(document.querySelector('#login-view').classList.contains('hidden')).toBe(false);
    expect(document.querySelector('#main-view').classList.contains('hidden')).toBe(true);
  });
});

describe('showStatus', () => {
  it('shows status message', async () => {
    const { showStatus } = await import('../popup/popup.js');
    showStatus('Synced 5 emails');

    const el = document.querySelector('#status-message');
    expect(el.classList.contains('hidden')).toBe(false);
    expect(el.textContent).toBe('Synced 5 emails');
    expect(el.classList.contains('error')).toBe(false);
  });

  it('shows error status', async () => {
    const { showStatus } = await import('../popup/popup.js');
    showStatus('Something failed', true);

    const el = document.querySelector('#status-message');
    expect(el.classList.contains('error')).toBe(true);
  });
});

describe('hideStatus', () => {
  it('hides the status message', async () => {
    const { showStatus, hideStatus } = await import('../popup/popup.js');
    showStatus('visible');
    hideStatus();

    expect(document.querySelector('#status-message').classList.contains('hidden')).toBe(true);
  });
});

describe('loadStats', () => {
  it('displays correct counts per priority', async () => {
    chrome.runtime.sendMessage.mockImplementation((msg) => {
      if (msg.params?.priority === 'high') return Promise.resolve({ total: 3 });
      if (msg.params?.priority === 'medium') return Promise.resolve({ total: 7 });
      if (msg.params?.priority === 'low') return Promise.resolve({ total: 12 });
      return Promise.resolve({});
    });

    const { loadStats } = await import('../popup/popup.js');
    await loadStats();

    expect(document.querySelector('#stat-high').textContent).toBe('3');
    expect(document.querySelector('#stat-medium').textContent).toBe('7');
    expect(document.querySelector('#stat-low').textContent).toBe('12');
  });

  it('shows error status on failure', async () => {
    chrome.runtime.sendMessage.mockRejectedValue(new Error('Network error'));

    const { loadStats } = await import('../popup/popup.js');
    await loadStats();

    const status = document.querySelector('#status-message');
    expect(status.classList.contains('hidden')).toBe(false);
    expect(status.classList.contains('error')).toBe(true);
  });
});

describe('setButtonLoading', () => {
  it('disables and re-enables button', async () => {
    const { setButtonLoading } = await import('../popup/popup.js');
    const btn = document.querySelector('#sync-btn');

    setButtonLoading(btn, true);
    expect(btn.disabled).toBe(true);

    setButtonLoading(btn, false);
    expect(btn.disabled).toBe(false);
  });
});
