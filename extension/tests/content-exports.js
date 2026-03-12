// Test helper: loads content.js (a classic script) and re-exports its functions.
// Content scripts can't use ES module syntax, so they assign to globalThis instead.
import '../content/content.js';

export const {
  extractGmailIdsFromDOM,
  injectBadge,
  removeBadges,
  scanAndInject,
  setupObserver,
} = globalThis.__epContentScript;
