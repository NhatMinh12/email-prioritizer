import { vi } from 'vitest';

function createStorageMock() {
  let store = {};
  return {
    _store: store,
    _reset() {
      store = {};
      this._store = store;
    },
    get: vi.fn((keys) => {
      const result = {};
      const keyList = typeof keys === 'string' ? [keys] : Array.isArray(keys) ? keys : Object.keys(keys);
      for (const k of keyList) {
        if (k in store) {
          result[k] = store[k];
        }
      }
      return Promise.resolve(result);
    }),
    set: vi.fn((items) => {
      Object.assign(store, items);
      return Promise.resolve();
    }),
    remove: vi.fn((keys) => {
      const keyList = typeof keys === 'string' ? [keys] : keys;
      for (const k of keyList) {
        delete store[k];
      }
      return Promise.resolve();
    }),
  };
}

const storageMock = createStorageMock();

global.chrome = {
  storage: {
    local: storageMock,
  },
  runtime: {
    sendMessage: vi.fn(),
    onMessage: {
      addListener: vi.fn(),
      removeListener: vi.fn(),
    },
    getURL: vi.fn((path) => `chrome-extension://test-id/${path}`),
  },
  tabs: {
    create: vi.fn(() => Promise.resolve({ id: 1 })),
    remove: vi.fn(() => Promise.resolve()),
    query: vi.fn(() => Promise.resolve([])),
    sendMessage: vi.fn(() => Promise.resolve()),
    onUpdated: {
      addListener: vi.fn(),
      removeListener: vi.fn(),
    },
  },
};

global.resetChromeMocks = () => {
  storageMock._reset();
  storageMock.get.mockClear();
  storageMock.set.mockClear();
  storageMock.remove.mockClear();
  chrome.runtime.sendMessage.mockReset();
  chrome.runtime.onMessage.addListener.mockClear();
  chrome.tabs.create.mockReset().mockResolvedValue({ id: 1 });
  chrome.tabs.remove.mockReset().mockResolvedValue();
  chrome.tabs.query.mockReset().mockResolvedValue([]);
  chrome.tabs.sendMessage.mockReset().mockResolvedValue();
  chrome.tabs.onUpdated.addListener.mockClear();
  chrome.tabs.onUpdated.removeListener.mockClear();
};
