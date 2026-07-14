import { useCallback, useEffect, useState } from 'react';
import { vault } from '../services/secureVault';

/**
 * React wrapper around the encrypted vault.
 * - `status`: 'locked' | 'unlocked' | 'empty' (no vault created yet)
 * - secrets are only ever accessed through getSecret(); names are listed safely.
 */
export function useVault() {
  const [status, setStatus] = useState('locked');
  const [error, setError] = useState(null);
  const [secretNames, setSecretNames] = useState([]);

  const refreshNames = useCallback(async () => {
    if (!vault.isUnlocked()) {
      setSecretNames([]);
      return;
    }
    setSecretNames(await vault.listSecrets());
  }, []);

  const unlock = useCallback(
    async (passphrase) => {
      setError(null);
      try {
        const ok = await vault.unlock(passphrase);
        if (ok) {
          setStatus('unlocked');
          await refreshNames();
          return true;
        }
        setError('Wrong passphrase.');
        return false;
      } catch (e) {
        setError(e.message || 'Failed to unlock vault.');
        return false;
      }
    },
    [refreshNames],
  );

  const lock = useCallback(() => {
    vault.lock();
    setStatus('locked');
    setSecretNames([]);
  }, []);

  const setSecret = useCallback(
    async (name, value) => {
      setError(null);
      try {
        await vault.setSecret(name, value);
        await refreshNames();
      } catch (e) {
        setError(e.message);
      }
    },
    [refreshNames],
  );

  const getSecret = useCallback(async (name) => {
    setError(null);
    try {
      return await vault.getSecret(name);
    } catch (e) {
      setError(e.message);
      return null;
    }
  }, []);

  const deleteSecret = useCallback(
    async (name) => {
      setError(null);
      try {
        await vault.deleteSecret(name);
        await refreshNames();
      } catch (e) {
        setError(e.message);
      }
    },
    [refreshNames],
  );

  useEffect(() => {
    // Determine initial status without exposing anything.
    (async () => {
      const raw = typeof localStorage !== 'undefined' ? localStorage.getItem('friday_vault_v1') : null;
      setStatus(raw ? 'locked' : 'empty');
    })();
  }, []);

  return { status, error, secretNames, unlock, lock, setSecret, getSecret, deleteSecret };
}
