import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { extractGmailIdsFromDOM, injectBadge, removeBadges, scanAndInject, setupObserver } from '../content/content.js';

beforeEach(() => {
  resetChromeMocks();
  document.body.innerHTML = '';
});

afterEach(() => {
  document.body.innerHTML = '';
});

/**
 * Build a mock Gmail inbox table with email rows.
 */
function buildGmailDOM(emails) {
  const table = document.createElement('table');
  const tbody = document.createElement('tbody');

  for (const email of emails) {
    const tr = document.createElement('tr');
    tr.className = 'zA';
    tr.setAttribute('role', 'row');

    // Add some td cells mimicking Gmail layout
    for (let i = 0; i < 3; i++) {
      tr.appendChild(document.createElement('td'));
    }

    // Sender cell (4th td)
    const senderTd = document.createElement('td');
    senderTd.className = 'yX xY';
    const senderSpan = document.createElement('span');
    senderSpan.textContent = email.sender || 'Sender';
    senderTd.appendChild(senderSpan);
    tr.appendChild(senderTd);

    // Subject cell with link containing Gmail ID
    const subjectTd = document.createElement('td');
    const link = document.createElement('a');
    link.href = `https://mail.google.com/mail/u/0/#inbox/${email.gmailId}`;
    link.textContent = email.subject || 'Subject';
    subjectTd.appendChild(link);
    tr.appendChild(subjectTd);

    tbody.appendChild(tr);
  }

  table.appendChild(tbody);
  document.body.appendChild(table);
  return table;
}

describe('extractGmailIdsFromDOM', () => {
  it('extracts Gmail IDs from inbox links', () => {
    buildGmailDOM([
      { gmailId: 'FMfcgzABC123', sender: 'Alice', subject: 'Hello' },
      { gmailId: 'FMfcgzDEF456', sender: 'Bob', subject: 'Meeting' },
    ]);

    const idMap = extractGmailIdsFromDOM();

    expect(idMap.size).toBe(2);
    expect(idMap.has('FMfcgzABC123')).toBe(true);
    expect(idMap.has('FMfcgzDEF456')).toBe(true);
  });

  it('handles search result links', () => {
    const table = document.createElement('table');
    const tr = document.createElement('tr');
    tr.className = 'zA';

    const td = document.createElement('td');
    const link = document.createElement('a');
    link.href = 'https://mail.google.com/mail/u/0/#search/query/FMfcgzSEARCH789';
    td.appendChild(link);
    tr.appendChild(td);
    table.appendChild(tr);
    document.body.appendChild(table);

    const idMap = extractGmailIdsFromDOM();

    expect(idMap.size).toBe(1);
    expect(idMap.has('FMfcgzSEARCH789')).toBe(true);
  });

  it('handles label links', () => {
    const table = document.createElement('table');
    const tr = document.createElement('tr');
    tr.className = 'zA';

    const td = document.createElement('td');
    const link = document.createElement('a');
    link.href = 'https://mail.google.com/mail/u/0/#label/Work/FMfcgzLABEL001';
    td.appendChild(link);
    tr.appendChild(td);
    table.appendChild(tr);
    document.body.appendChild(table);

    const idMap = extractGmailIdsFromDOM();

    expect(idMap.size).toBe(1);
    expect(idMap.has('FMfcgzLABEL001')).toBe(true);
  });

  it('returns empty map when no email rows found', () => {
    document.body.innerHTML = '<div>No emails here</div>';
    const idMap = extractGmailIdsFromDOM();
    expect(idMap.size).toBe(0);
  });

  it('returns empty map when rows have no matching links', () => {
    const table = document.createElement('table');
    const tr = document.createElement('tr');
    tr.className = 'zA';
    const td = document.createElement('td');
    const link = document.createElement('a');
    link.href = 'https://example.com';
    td.appendChild(link);
    tr.appendChild(td);
    table.appendChild(tr);
    document.body.appendChild(table);

    const idMap = extractGmailIdsFromDOM();
    expect(idMap.size).toBe(0);
  });
});

describe('injectBadge', () => {
  it('creates dot with correct color for high priority', () => {
    buildGmailDOM([{ gmailId: 'g1', sender: 'Alice' }]);
    const row = document.querySelector('tr.zA');

    injectBadge(row, { priority: 'high', urgency: 'normal' });

    const dot = row.querySelector('.ep-priority-dot');
    expect(dot).not.toBeNull();
    expect(dot.style.backgroundColor).toBe('rgb(239, 68, 68)'); // #ef4444
  });

  it('creates dot with correct color for medium priority', () => {
    buildGmailDOM([{ gmailId: 'g1' }]);
    const row = document.querySelector('tr.zA');

    injectBadge(row, { priority: 'medium', urgency: 'normal' });

    const dot = row.querySelector('.ep-priority-dot');
    expect(dot.style.backgroundColor).toBe('rgb(245, 158, 11)'); // #f59e0b
  });

  it('creates dot with correct color for low priority', () => {
    buildGmailDOM([{ gmailId: 'g1' }]);
    const row = document.querySelector('tr.zA');

    injectBadge(row, { priority: 'low', urgency: 'normal' });

    const dot = row.querySelector('.ep-priority-dot');
    expect(dot.style.backgroundColor).toBe('rgb(16, 185, 129)'); // #10b981
  });

  it('does not double-inject on same row', () => {
    buildGmailDOM([{ gmailId: 'g1' }]);
    const row = document.querySelector('tr.zA');

    injectBadge(row, { priority: 'high', urgency: 'normal' });
    injectBadge(row, { priority: 'high', urgency: 'normal' });

    const dots = row.querySelectorAll('.ep-priority-dot');
    expect(dots.length).toBe(1);
  });

  it('sets tooltip with urgency when not normal', () => {
    buildGmailDOM([{ gmailId: 'g1' }]);
    const row = document.querySelector('tr.zA');

    injectBadge(row, { priority: 'high', urgency: 'urgent' });

    const dot = row.querySelector('.ep-priority-dot');
    expect(dot.title).toContain('High priority');
    expect(dot.title).toContain('Urgent');
  });

  it('does not show urgency label for normal urgency', () => {
    buildGmailDOM([{ gmailId: 'g1' }]);
    const row = document.querySelector('tr.zA');

    injectBadge(row, { priority: 'low', urgency: 'normal' });

    const dot = row.querySelector('.ep-priority-dot');
    expect(dot.title).toBe('Low priority');
    expect(dot.title).not.toContain('Normal');
  });

  it('includes response needed in tooltip', () => {
    buildGmailDOM([{ gmailId: 'g1' }]);
    const row = document.querySelector('tr.zA');

    injectBadge(row, { priority: 'high', urgency: 'normal', needs_response: true });

    const dot = row.querySelector('.ep-priority-dot');
    expect(dot.title).toContain('Response needed');
  });

  it('inserts badge into sender cell', () => {
    buildGmailDOM([{ gmailId: 'g1', sender: 'Alice' }]);
    const row = document.querySelector('tr.zA');

    injectBadge(row, { priority: 'medium', urgency: 'normal' });

    const senderCell = row.querySelector('td.yX');
    expect(senderCell.querySelector('.ep-priority-dot')).not.toBeNull();
    // Badge should be first child
    expect(senderCell.firstChild.className).toBe('ep-priority-dot');
  });
});

describe('removeBadges', () => {
  it('removes all injected badges', () => {
    buildGmailDOM([
      { gmailId: 'g1' },
      { gmailId: 'g2' },
    ]);
    const rows = document.querySelectorAll('tr.zA');
    injectBadge(rows[0], { priority: 'high', urgency: 'normal' });
    injectBadge(rows[1], { priority: 'low', urgency: 'normal' });

    expect(document.querySelectorAll('.ep-priority-dot').length).toBe(2);

    removeBadges();

    expect(document.querySelectorAll('.ep-priority-dot').length).toBe(0);
  });
});

describe('scanAndInject', () => {
  it('requests classifications and injects badges for matched emails', async () => {
    buildGmailDOM([
      { gmailId: 'g1', sender: 'Alice' },
      { gmailId: 'g2', sender: 'Bob' },
      { gmailId: 'g3', sender: 'Charlie' },
    ]);

    // Background returns classifications for g1 and g3 only
    chrome.runtime.sendMessage.mockResolvedValue({
      g1: { priority: 'high', urgency: 'urgent' },
      g3: { priority: 'low', urgency: 'normal' },
    });

    await scanAndInject();

    const dots = document.querySelectorAll('.ep-priority-dot');
    expect(dots.length).toBe(2);

    // Verify correct messages were sent
    expect(chrome.runtime.sendMessage).toHaveBeenCalledWith({
      type: 'GET_CLASSIFICATIONS',
      gmailIds: expect.arrayContaining(['g1', 'g2', 'g3']),
    });
  });

  it('does nothing when no email rows are found', async () => {
    document.body.innerHTML = '<div>Empty</div>';

    await scanAndInject();

    expect(chrome.runtime.sendMessage).not.toHaveBeenCalled();
  });

  it('handles sendMessage errors gracefully', async () => {
    buildGmailDOM([{ gmailId: 'g1' }]);
    chrome.runtime.sendMessage.mockRejectedValue(new Error('Extension context invalidated'));

    // Should not throw
    await scanAndInject();

    expect(document.querySelectorAll('.ep-priority-dot').length).toBe(0);
  });

  it('handles error response from background', async () => {
    buildGmailDOM([{ gmailId: 'g1' }]);
    chrome.runtime.sendMessage.mockResolvedValue({ error: 'Not authenticated' });

    await scanAndInject();

    expect(document.querySelectorAll('.ep-priority-dot').length).toBe(0);
  });
});

describe('setupObserver', () => {
  it('creates a MutationObserver on document.body', () => {
    const observer = setupObserver();
    expect(observer).toBeDefined();
    expect(observer).toBeInstanceOf(MutationObserver);
    observer.disconnect(); // cleanup
  });
});
