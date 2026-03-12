import { describe, it, expect, vi, beforeEach } from 'vitest';
import { handleMessage, classificationCache } from '../background.js';
import { MSG, STORAGE_KEYS } from '../lib/constants.js';

global.fetch = vi.fn();

beforeEach(() => {
  resetChromeMocks();
  global.fetch.mockReset();
  classificationCache.clear();
});

function mockApiFetch(data) {
  global.fetch.mockResolvedValue({
    ok: true,
    status: 200,
    json: () => Promise.resolve(data),
  });
}

describe('handleMessage', () => {
  describe('GET_AUTH_STATE', () => {
    it('returns authenticated: false when no token stored', async () => {
      const result = await handleMessage({ type: MSG.GET_AUTH_STATE });
      expect(result).toEqual({ authenticated: false });
    });

    it('returns authenticated: true with user when token is valid', async () => {
      await chrome.storage.local.set({ [STORAGE_KEYS.TOKEN]: 'valid-token' });
      mockApiFetch({ id: 'user-1', email: 'test@example.com' });

      const result = await handleMessage({ type: MSG.GET_AUTH_STATE });

      expect(result).toEqual({
        authenticated: true,
        user: { id: 'user-1', email: 'test@example.com' },
      });
    });

    it('returns authenticated: false when token is expired', async () => {
      await chrome.storage.local.set({ [STORAGE_KEYS.TOKEN]: 'expired' });
      global.fetch.mockResolvedValue({
        ok: false,
        status: 401,
        json: () => Promise.resolve({}),
      });

      const result = await handleMessage({ type: MSG.GET_AUTH_STATE });
      expect(result).toEqual({ authenticated: false });
    });
  });

  describe('LOGIN', () => {
    it('opens a tab with the authorization URL and stores the tab ID', async () => {
      global.fetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ authorization_url: 'https://accounts.google.com/o/oauth2' }),
      });

      const result = await handleMessage({ type: MSG.LOGIN });

      expect(chrome.tabs.create).toHaveBeenCalledWith({
        url: 'https://accounts.google.com/o/oauth2',
      });
      expect(result).toEqual({ success: true, pending: true });

      // Verify the tab ID was persisted so the top-level listener can match it
      const stored = await chrome.storage.local.get(STORAGE_KEYS.LOGIN_TAB_ID);
      expect(stored[STORAGE_KEYS.LOGIN_TAB_ID]).toBe(1); // mock returns { id: 1 }
    });

    it('throws when /auth/login request fails', async () => {
      global.fetch.mockResolvedValue({
        ok: false,
        status: 500,
        json: () => Promise.resolve({}),
      });

      await expect(handleMessage({ type: MSG.LOGIN })).rejects.toThrow('Failed to get login URL');
    });
  });

  describe('LOGOUT', () => {
    it('clears token and classification cache', async () => {
      await chrome.storage.local.set({ [STORAGE_KEYS.TOKEN]: 'token' });
      classificationCache.set('gmail1', { priority: 'high' });

      const result = await handleMessage({ type: MSG.LOGOUT });

      expect(result).toEqual({ success: true });
      expect(chrome.storage.local.remove).toHaveBeenCalledWith(STORAGE_KEYS.TOKEN);
      expect(classificationCache.size).toBe(0);
    });
  });

  describe('GET_EMAILS', () => {
    it('returns emails and updates classification cache', async () => {
      await chrome.storage.local.set({ [STORAGE_KEYS.TOKEN]: 'token' });
      const emailData = {
        emails: [
          {
            id: '1',
            gmail_id: 'gmail-abc',
            subject: 'Test',
            classification: { priority: 'high', urgency: 'urgent' },
          },
          {
            id: '2',
            gmail_id: 'gmail-def',
            subject: 'Test 2',
            classification: null,
          },
        ],
        total: 2,
        page: 1,
        page_size: 20,
      };
      mockApiFetch(emailData);

      const result = await handleMessage({ type: MSG.GET_EMAILS, params: { page: 1 } });

      expect(result.emails).toHaveLength(2);
      expect(classificationCache.get('gmail-abc')).toEqual({ priority: 'high', urgency: 'urgent' });
      expect(classificationCache.has('gmail-def')).toBe(false); // no classification
    });
  });

  describe('SYNC_EMAILS', () => {
    it('calls sync and refreshes cache when emails synced', async () => {
      await chrome.storage.local.set({ [STORAGE_KEYS.TOKEN]: 'token' });
      // First call: sync response, second call: getEmails for cache refresh
      global.fetch
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: () => Promise.resolve({ synced: 5 }),
        })
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: () => Promise.resolve({
            emails: [{ gmail_id: 'g1', classification: { priority: 'low' } }],
            total: 1,
          }),
        });

      const result = await handleMessage({ type: MSG.SYNC_EMAILS });

      expect(result).toEqual({ synced: 5 });
      expect(classificationCache.get('g1')).toEqual({ priority: 'low' });
    });
  });

  describe('CLASSIFY_EMAILS', () => {
    it('calls classify and refreshes cache', async () => {
      await chrome.storage.local.set({ [STORAGE_KEYS.TOKEN]: 'token' });
      global.fetch
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: () => Promise.resolve({ classified: 3, message: 'Classified 3 emails' }),
        })
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: () => Promise.resolve({
            emails: [{ gmail_id: 'g2', classification: { priority: 'medium' } }],
            total: 1,
          }),
        });

      const result = await handleMessage({ type: MSG.CLASSIFY_EMAILS });

      expect(result.classified).toBe(3);
      expect(classificationCache.get('g2')).toEqual({ priority: 'medium' });
    });
  });

  describe('GET_CLASSIFICATIONS', () => {
    it('returns cached classifications for requested IDs', () => {
      classificationCache.set('g1', { priority: 'high' });
      classificationCache.set('g2', { priority: 'low' });

      const result = handleMessage({
        type: MSG.GET_CLASSIFICATIONS,
        gmailIds: ['g1', 'g2', 'g3'],
      });

      // GET_CLASSIFICATIONS is sync internally but handleMessage is async
      return result.then((res) => {
        expect(res).toEqual({
          g1: { priority: 'high' },
          g2: { priority: 'low' },
        });
        expect(res.g3).toBeUndefined();
      });
    });

    it('returns empty object when no gmailIds provided', async () => {
      const result = await handleMessage({ type: MSG.GET_CLASSIFICATIONS });
      expect(result).toEqual({});
    });
  });

  describe('unknown message type', () => {
    it('returns error for unknown message type', async () => {
      const result = await handleMessage({ type: 'UNKNOWN_TYPE' });
      expect(result).toEqual({ error: 'Unknown message type: UNKNOWN_TYPE' });
    });
  });
});
