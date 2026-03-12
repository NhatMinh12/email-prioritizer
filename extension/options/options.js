import { API_BASE_URL, STORAGE_KEYS } from '../lib/constants.js';

const $ = (sel) => document.querySelector(sel);

async function loadSettings() {
  const result = await chrome.storage.local.get([
    STORAGE_KEYS.API_BASE_URL,
    STORAGE_KEYS.BADGES_ENABLED,
  ]);

  $('#api-url').value = result[STORAGE_KEYS.API_BASE_URL] || API_BASE_URL;

  // Default to true if not explicitly set
  const badgesEnabled = result[STORAGE_KEYS.BADGES_ENABLED] !== false;
  $('#badges-enabled').checked = badgesEnabled;

  // Update the full settings link to match the configured API URL
  updateSettingsLink(result[STORAGE_KEYS.API_BASE_URL] || API_BASE_URL);
}

function updateSettingsLink(apiUrl) {
  // Derive frontend URL from API URL (port 3000 instead of 8000)
  try {
    const url = new URL(apiUrl);
    url.port = '3000';
    $('#full-settings-link').href = `${url.origin}/settings`;
  } catch {
    // Keep default
  }
}

async function saveSettings() {
  const apiUrl = $('#api-url').value.trim() || API_BASE_URL;
  const badgesEnabled = $('#badges-enabled').checked;

  await chrome.storage.local.set({
    [STORAGE_KEYS.API_BASE_URL]: apiUrl,
    [STORAGE_KEYS.BADGES_ENABLED]: badgesEnabled,
  });

  updateSettingsLink(apiUrl);

  const status = $('#status');
  status.classList.remove('hidden');
  setTimeout(() => status.classList.add('hidden'), 2000);
}

$('#save-btn').addEventListener('click', saveSettings);

loadSettings();

export { loadSettings, saveSettings };
