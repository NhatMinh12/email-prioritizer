import { describe, it, expect, vi, beforeEach } from 'vitest';
import { apiFetch, api } from '../lib/api.js';
import { STORAGE_KEYS } from '../lib/constants.js';

// Mock global fetch
global.fetch = vi.fn();

beforeEach(() => {
  resetChromeMocks();
  global.fetch.mockReset();
});

function mockFetchOk(data) {
  global.fetch.mockResolvedValue({
    ok: true,
    status: 200,
    json: () => Promise.resolve(data),
  });
}

function mockFetchError(status, detail) {
  global.fetch.mockResolvedValue({
    ok: false,
    status,
    json: () => Promise.resolve({ detail }),
  });
}

describe('apiFetch', () => {
  it('adds Authorization header when token is stored', async () => {
    await chrome.storage.local.set({ [STORAGE_KEYS.TOKEN]: 'test-jwt' });
    mockFetchOk({ ok: true });

    await apiFetch('/test');

    expect(global.fetch).toHaveBeenCalledWith(
      'http://localhost:8000/test',
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: 'Bearer test-jwt',
        }),
      })
    );
  });

  it('does not add Authorization header when no token stored', async () => {
    mockFetchOk({ ok: true });

    await apiFetch('/test');

    const callHeaders = global.fetch.mock.calls[0][1].headers;
    expect(callHeaders.Authorization).toBeUndefined();
  });

  it('always sets Content-Type to application/json', async () => {
    mockFetchOk({ ok: true });

    await apiFetch('/test');

    expect(global.fetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        headers: expect.objectContaining({
          'Content-Type': 'application/json',
        }),
      })
    );
  });

  it('clears token and throws on 401 response', async () => {
    await chrome.storage.local.set({ [STORAGE_KEYS.TOKEN]: 'expired-token' });
    global.fetch.mockResolvedValue({
      ok: false,
      status: 401,
      json: () => Promise.resolve({}),
    });

    await expect(apiFetch('/test')).rejects.toThrow('Token expired');
    expect(chrome.storage.local.remove).toHaveBeenCalledWith(STORAGE_KEYS.TOKEN);
  });

  it('throws with detail message on non-OK response', async () => {
    mockFetchError(422, 'Invalid feedback value');

    await expect(apiFetch('/test')).rejects.toThrow('Invalid feedback value');
  });

  it('throws with generic message when response has no detail', async () => {
    global.fetch.mockResolvedValue({
      ok: false,
      status: 500,
      json: () => Promise.reject(new Error('not json')),
    });

    await expect(apiFetch('/test')).rejects.toThrow('API error: 500');
  });

  it('uses custom API base URL from storage', async () => {
    await chrome.storage.local.set({
      [STORAGE_KEYS.API_BASE_URL]: 'https://api.example.com',
    });
    mockFetchOk({ ok: true });

    await apiFetch('/test');

    expect(global.fetch).toHaveBeenCalledWith(
      'https://api.example.com/test',
      expect.any(Object)
    );
  });

  it('passes through additional fetch options', async () => {
    mockFetchOk({ ok: true });

    await apiFetch('/test', { method: 'POST', body: '{"a":1}' });

    expect(global.fetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        method: 'POST',
        body: '{"a":1}',
      })
    );
  });
});

describe('api methods', () => {
  beforeEach(() => {
    mockFetchOk({});
  });

  it('getLoginUrl calls /auth/login', async () => {
    await api.getLoginUrl();
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/auth/login'),
      expect.any(Object)
    );
  });

  it('getMe calls /auth/me', async () => {
    await api.getMe();
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/auth/me'),
      expect.any(Object)
    );
  });

  it('getEmails passes query params correctly', async () => {
    await api.getEmails({ page: 2, page_size: 10, priority: 'high' });
    const url = global.fetch.mock.calls[0][0];
    expect(url).toContain('/api/emails?');
    expect(url).toContain('page=2');
    expect(url).toContain('page_size=10');
    expect(url).toContain('priority=high');
  });

  it('getEmails filters out null/empty params', async () => {
    await api.getEmails({ page: 1, priority: null, other: '' });
    const url = global.fetch.mock.calls[0][0];
    expect(url).toContain('page=1');
    expect(url).not.toContain('priority');
    expect(url).not.toContain('other');
  });

  it('syncEmails uses POST method', async () => {
    await api.syncEmails();
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/emails/sync'),
      expect.objectContaining({ method: 'POST' })
    );
  });

  it('classifyEmails uses POST with optional email_ids', async () => {
    await api.classifyEmails(['id1', 'id2']);
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/emails/classify'),
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ email_ids: ['id1', 'id2'] }),
      })
    );
  });

  it('classifyEmails sends no body when no ids provided', async () => {
    await api.classifyEmails();
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/emails/classify'),
      expect.objectContaining({
        method: 'POST',
        body: undefined,
      })
    );
  });

  it('submitFeedback sends correct body', async () => {
    await api.submitFeedback('email-123', 'correct');
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/emails/email-123/feedback'),
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ feedback: 'correct' }),
      })
    );
  });
});
