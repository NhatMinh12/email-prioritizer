// Content script for Gmail — injects priority badges into email rows.
// Communicates with background service worker via chrome.runtime.sendMessage.

const PRIORITY_COLORS = {
  high: '#ef4444',
  medium: '#f59e0b',
  low: '#10b981',
};

const URGENCY_LABELS = {
  urgent: 'Urgent',
  time_sensitive: 'Time-sensitive',
  normal: null,
  low: 'Low',
};

const MSG_GET_CLASSIFICATIONS = 'GET_CLASSIFICATIONS';
const MSG_CLASSIFICATIONS_UPDATED = 'CLASSIFICATIONS_UPDATED';

// Gmail thread/message ID regex — captures the last path segment from the hash.
// Handles #inbox/ID, #search/query/ID, #label/Name/ID, #sent/ID, etc.
const GMAIL_ID_REGEX = /#.*\/([A-Za-z0-9_-]+)$/;

// Selectors to try for email rows (Gmail DOM is unstable, multiple fallbacks)
const ROW_SELECTORS = [
  'tr.zA',           // Gmail's primary email row class
  'tr[role="row"]',  // ARIA role-based
  'div[role="main"] table tbody tr', // structural
];

let debounceTimer = null;
const DEBOUNCE_MS = 300;

/**
 * Extract Gmail thread/message IDs from the currently visible email rows.
 * Returns a Map of gmailId -> row element.
 */
function extractGmailIdsFromDOM() {
  const idMap = new Map();

  // Try each selector until we find rows
  let rows = [];
  for (const selector of ROW_SELECTORS) {
    rows = document.querySelectorAll(selector);
    if (rows.length > 0) break;
  }

  for (const row of rows) {
    // Look for anchor tags that contain Gmail thread IDs in the href
    const links = row.querySelectorAll('a[href*="#"]');
    for (const link of links) {
      const href = link.getAttribute('href');
      if (!href) continue;

      const match = href.match(GMAIL_ID_REGEX);
      if (match) {
        idMap.set(match[1], row);
        break; // one ID per row is enough
      }
    }
  }

  return idMap;
}

/**
 * Inject a colored priority dot badge into a Gmail email row.
 */
function injectBadge(row, classification) {
  // Don't double-inject
  if (row.querySelector('.ep-priority-dot')) return;

  const { priority, urgency } = classification;
  const color = PRIORITY_COLORS[priority];
  if (!color) return;

  const dot = document.createElement('span');
  dot.className = 'ep-priority-dot';
  dot.style.backgroundColor = color;

  // Build tooltip text
  let tooltip = `${priority.charAt(0).toUpperCase() + priority.slice(1)} priority`;
  const urgencyLabel = URGENCY_LABELS[urgency];
  if (urgencyLabel) {
    tooltip += ` · ${urgencyLabel}`;
  }
  if (classification.needs_response) {
    tooltip += ' · Response needed';
  }
  dot.setAttribute('data-tooltip', tooltip);
  dot.title = tooltip;

  // Try to insert before the sender text in various Gmail layouts
  // Gmail sender cells are typically td:nth-child(4) or td elements with specific classes
  const senderCell =
    row.querySelector('td.yX.xY') ||      // Gmail's sender column class
    row.querySelector('td:nth-child(4)') ||
    row.querySelector('td:nth-child(3)') ||
    row.querySelector('td:nth-child(2)');

  if (senderCell) {
    senderCell.style.position = 'relative';
    senderCell.insertBefore(dot, senderCell.firstChild);
  }
}

/**
 * Remove all injected badges from the DOM.
 */
function removeBadges() {
  const dots = document.querySelectorAll('.ep-priority-dot');
  for (const dot of dots) {
    dot.remove();
  }
}

/**
 * Scan visible email rows, request classifications from background, inject badges.
 */
async function scanAndInject() {
  const idMap = extractGmailIdsFromDOM();
  if (idMap.size === 0) return;

  const gmailIds = Array.from(idMap.keys());

  try {
    const classifications = await chrome.runtime.sendMessage({
      type: MSG_GET_CLASSIFICATIONS,
      gmailIds,
    });

    if (!classifications || classifications.error) return;

    for (const [gmailId, row] of idMap) {
      if (classifications[gmailId]) {
        injectBadge(row, classifications[gmailId]);
      }
    }
  } catch {
    // Extension context invalidated or background not ready — silently ignore
  }
}

/**
 * Set up MutationObserver to detect Gmail DOM changes and re-inject badges.
 */
function setupObserver() {
  const observer = new MutationObserver(() => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(scanAndInject, DEBOUNCE_MS);
  });

  observer.observe(document.body, {
    childList: true,
    subtree: true,
  });

  return observer;
}

/**
 * Listen for classification cache updates from the background service worker.
 */
function listenForUpdates() {
  chrome.runtime.onMessage.addListener((message) => {
    if (message.type === MSG_CLASSIFICATIONS_UPDATED) {
      // Remove old badges and re-inject with new data
      removeBadges();
      scanAndInject();
    }
  });
}

// Initialize
function main() {
  // Initial scan after a short delay to let Gmail finish rendering
  setTimeout(scanAndInject, 1000);
  setupObserver();
  listenForUpdates();
}

main();

// Expose for testing — Vitest test files import from a wrapper module
// (see tests/content-exports.js). In Chrome, this is just a no-op assignment.
if (typeof globalThis !== 'undefined') {
  globalThis.__epContentScript = {
    extractGmailIdsFromDOM,
    injectBadge,
    removeBadges,
    scanAndInject,
    setupObserver,
  };
}
