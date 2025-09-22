// API runtime configuration manager for switching between servers A, B, C and fixed D (127.0.0.1:8000)
// Handles persistence via localStorage and exposes helpers used by api service

const STORAGE_KEYS = {
  serverA: 'frbot.serverA',
  serverB: 'frbot.serverB',
  serverC: 'frbot.serverC',
  active: 'frbot.activeServer', // 'A' | 'B' | 'C' | 'D'
};

const FIXED_SERVER_D = 'http://127.0.0.1:8000';

// Basic URL sanitizer: ensure protocol is present, default to http://
function normalizeBaseUrl(input) {
  if (!input) return '';
  let value = String(input).trim();
  if (!/^https?:\/\//i.test(value)) {
    value = 'http://' + value;
  }
  // remove trailing slash
  value = value.replace(/\/$/, '');
  try {
    // Validate URL
    // eslint-disable-next-line no-new
    new URL(value);
    return value;
  } catch (_) {
    return '';
  }
}

function getStored(key, fallback = '') {
  try {
    const v = window.localStorage.getItem(key);
    return v ?? fallback;
  } catch (_) {
    return fallback;
  }
}

function setStored(key, value) {
  try {
    if (value === undefined || value === null) {
      window.localStorage.removeItem(key);
    } else {
      window.localStorage.setItem(key, String(value));
    }
  } catch (_) {
    // ignore
  }
}

export function getServers(defaultBaseUrl) {
  const serverA = getStored(STORAGE_KEYS.serverA, '');
  const serverB = getStored(STORAGE_KEYS.serverB, '');
  const serverC = getStored(STORAGE_KEYS.serverC, '');
  let active = getStored(STORAGE_KEYS.active, '');

  // If nothing set yet, seed serverA with provided default
  if (!serverA && defaultBaseUrl) {
    setStored(STORAGE_KEYS.serverA, defaultBaseUrl);
  }
  if (!active) {
    active = 'A';
    setStored(STORAGE_KEYS.active, active);
  }

  return {
    A: serverA || defaultBaseUrl || '',
    B: serverB || '',
    C: serverC || '',
    D: FIXED_SERVER_D,
    active, // 'A' | 'B' | 'C' | 'D'
  };
}

export function setServerUrl(key /* 'A' | 'B' | 'C' */, url) {
  const normalized = normalizeBaseUrl(url);
  if (key === 'A') setStored(STORAGE_KEYS.serverA, normalized);
  if (key === 'B') setStored(STORAGE_KEYS.serverB, normalized);
  if (key === 'C') setStored(STORAGE_KEYS.serverC, normalized);
  // D is fixed and not settable
  return normalized;
}

export function setActiveServer(key /* 'A' | 'B' | 'C' | 'D' */) {
  if (!['A', 'B', 'C', 'D'].includes(key)) return;
  setStored(STORAGE_KEYS.active, key);
}

export function getActiveBaseUrl(defaultBaseUrl) {
  const { A, B, C, D, active } = getServers(defaultBaseUrl);
  let candidate = A;
  if (active === 'B') candidate = B;
  if (active === 'C') candidate = C;
  if (active === 'D') candidate = D;
  const normalized = normalizeBaseUrl(candidate || defaultBaseUrl || '');
  return normalized || '';
}

export function resetServers() {
  setStored(STORAGE_KEYS.serverA, '');
  setStored(STORAGE_KEYS.serverB, '');
  setStored(STORAGE_KEYS.serverC, '');
  setStored(STORAGE_KEYS.active, 'A');
}
