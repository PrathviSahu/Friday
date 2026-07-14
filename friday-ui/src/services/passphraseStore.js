// Local storage of the owner's spoken access phrases (unlock + lock).
// This is a client-side gate: the secret phrase itself is the credential.
const UNLOCK_KEY = 'friday_unlock_phrase';
const LOCK_KEY = 'friday_lock_phrase';

// Normalize a phrase the same way we normalize speech transcripts so a spoken
// phrase matches a typed one: lowercase, keep alphanumerics + spaces only,
// collapse whitespace.
export function normalize(text = '') {
    return String(text)
        .toLowerCase()
        .replace(/[^a-z0-9 ]/g, ' ')
        .replace(/\s+/g, ' ')
        .trim();
}

export function getPassphrases() {
    try {
        const unlock = localStorage.getItem(UNLOCK_KEY);
        const lock = localStorage.getItem(LOCK_KEY);
        return { unlock: unlock || '', lock: lock || '' };
    } catch {
        return { unlock: '', lock: '' };
    }
}

export function hasPassphrases() {
    const { unlock, lock } = getPassphrases();
    return Boolean(unlock && lock);
}

export function setPassphrases({ unlock, lock }) {
    const u = normalize(unlock);
    const l = normalize(lock);
    try {
        if (u) localStorage.setItem(UNLOCK_KEY, u);
        if (l) localStorage.setItem(LOCK_KEY, l);
    } catch {
        /* storage unavailable — non-fatal for dev */
    }
    return { unlock: u, lock: l };
}

export function clearPassphrases() {
    try {
        localStorage.removeItem(UNLOCK_KEY);
        localStorage.removeItem(LOCK_KEY);
    } catch {
        /* ignore */
    }
}
