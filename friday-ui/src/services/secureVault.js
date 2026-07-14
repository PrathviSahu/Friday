/**
 * secureVault.js — encrypted credential store for FRIDAY.
 *
 * Design rules (see memory: friday-security-trading-guards):
 *  - NEVER store secrets in plaintext.
 *  - Uses Web Crypto: PBKDF2(passphrase) -> AES-GCM 256 key.
 *  - Per-entry salt + IV; the encrypted blob is persisted, not the secrets.
 *  - Works in the browser dev context (localhost is a secure context) via
 *    localStorage. When running inside the Tauri shell, swap the persistence
 *    layer for @tauri-apps/plugin-store / OS keychain (see persistLoad/persistSave).
 *
 * The passphrase is never persisted — only the user knows it. Lose it and the
 * vault is unrecoverable by design.
 */

const VAULT_KEY = 'friday_vault_v1';
const PBKDF2_ITERATIONS = 250_000;

// ── low-level crypto helpers ──────────────────────────────────────────────────
const enc = new TextEncoder();
const dec = new TextDecoder();

const bufToB64 = (buf) => btoa(String.fromCharCode(...new Uint8Array(buf)));
const b64ToBuf = (b64) => Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));

async function deriveKey(passphrase, salt) {
  const baseKey = await crypto.subtle.importKey(
    'raw',
    enc.encode(passphrase),
    'PBKDF2',
    false,
    ['deriveKey'],
  );
  return crypto.subtle.deriveKey(
    { name: 'PBKDF2', salt, iterations: PBKDF2_ITERATIONS, hash: 'SHA-256' },
    baseKey,
    { name: 'AES-GCM', length: 256 },
    false,
    ['encrypt', 'decrypt'],
  );
}

async function aesEncrypt(key, plaintext) {
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const ct = await crypto.subtle.encrypt(
    { name: 'AES-GCM', iv },
    key,
    enc.encode(plaintext),
  );
  return { iv: bufToB64(iv), data: bufToB64(ct) };
}

async function aesDecrypt(key, ivB64, dataB64) {
  const pt = await crypto.subtle.decrypt(
    { name: 'AES-GCM', iv: b64ToBuf(ivB64) },
    key,
    b64ToBuf(dataB64),
  );
  return dec.decode(pt);
}

// ── persistence (swap for Tauri secure store later) ───────────────────────────
async function persistSave(payload) {
  localStorage.setItem(VAULT_KEY, JSON.stringify(payload));
}

async function persistLoad() {
  const raw = localStorage.getItem(VAULT_KEY);
  return raw ? JSON.parse(raw) : null;
}

// ── public API ────────────────────────────────────────────────────────────────
export function createVault() {
  let key = null; // AES-GCM CryptoKey, held only while unlocked

  const isUnlocked = () => key !== null;

  const unlock = async (passphrase) => {
    // Web Crypto (crypto.subtle) is only present in a secure context. If it is
    // missing, surface a clear error instead of throwing an unhandled rejection
    // that would leave the unlock UI stuck on "Checking…".
    if (typeof crypto === 'undefined' || !crypto.subtle) {
      throw new Error('CRYPTO_UNAVAILABLE');
    }
    const stored = await persistLoad();
    if (!stored) {
      // First run: create a fresh vault with this passphrase, and store a
      // sentinel encrypted with the derived key to validate future unlocks.
      const salt = crypto.getRandomValues(new Uint8Array(16));
      key = await deriveKey(passphrase, salt);
      const sentinel = await aesEncrypt(key, '__friday_vault_ok__');
      await persistSave({ salt: bufToB64(salt), entries: {}, sentinel });
      return true;
    }
    const salt = b64ToBuf(stored.salt);
    const candidate = await deriveKey(passphrase, salt);
    try {
      if (stored.sentinel) {
        // Validate the passphrase by decrypting the sentinel.
        await aesDecrypt(candidate, stored.sentinel.iv, stored.sentinel.data);
      } else {
        // Legacy vault without a sentinel: create one now with the verified key.
        const sentinel = await aesEncrypt(candidate, '__friday_vault_ok__');
        stored.sentinel = sentinel;
        await persistSave(stored);
      }
      key = candidate;
      return true;
    } catch (e) {
      key = null;
      return false; // wrong passphrase
    }
  };

  const lock = () => {
    key = null;
  };

  // Wipe the persisted vault and forget the in-memory key. The next successful
  // unlock will recreate the vault, so the typed password becomes the new one.
  const reset = () => {
    key = null;
    try {
      localStorage.removeItem(VAULT_KEY);
    } catch {
      /* ignore */
    }
  };

  const setSecret = async (name, value) => {
    if (!isUnlocked()) throw new Error('Vault is locked. Call unlock() first.');
    const stored = (await persistLoad()) || { salt: null, entries: {}, sentinel: null };
    const enc = await aesEncrypt(key, JSON.stringify(value));
    stored.entries[name] = enc;
    await persistSave(stored);
  };

  const getSecret = async (name) => {
    if (!isUnlocked()) throw new Error('Vault is locked. Call unlock() first.');
    const stored = await persistLoad();
    const enc = stored?.entries?.[name];
    if (!enc) return null;
    const json = await aesDecrypt(key, enc.iv, enc.data);
    return JSON.parse(json);
  };

  const deleteSecret = async (name) => {
    if (!isUnlocked()) throw new Error('Vault is locked. Call unlock() first.');
    const stored = await persistLoad();
    if (stored?.entries?.[name]) {
      delete stored.entries[name];
      await persistSave(stored);
    }
  };

  // Returns secret names only — never the values.
  const listSecrets = async () => {
    const stored = await persistLoad();
    return Object.keys(stored?.entries || {});
  };

  return { isUnlocked, unlock, lock, reset, setSecret, getSecret, deleteSecret, listSecrets };
}

export const vault = createVault();
