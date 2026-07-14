// Fingerprint (platform authenticator) unlock via the WebAuthn Credential
// Management API. Works in secure contexts (https / localhost / 127.0.0.1).
// No backend required for a personal local device — the credential is stored
// locally and the challenge is generated per attempt.

const CRED_KEY = 'friday_fingerprint_cred';

function bufToBase64url(buf) {
    const bytes = new Uint8Array(buf);
    let str = '';
    for (let i = 0; i < bytes.length; i += 1) str += String.fromCharCode(bytes[i]);
    return btoa(str).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

function base64urlToBuf(str) {
    const padded = str.replace(/-/g, '+').replace(/_/g, '/');
    const bin = atob(padded);
    const bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i += 1) bytes[i] = bin.charCodeAt(i);
    return bytes.buffer;
}

function randomChallenge() {
    const arr = new Uint8Array(32);
    crypto.getRandomValues(arr);
    return arr;
}

// WebAuthn requires a valid RP ID: a registrable domain, or "localhost" in a
// secure context. The RP ID must match the page's effective domain, so we use
// the real hostname. The dev server MUST be opened via http://localhost:PORT
// (never the 127.0.0.1 IP literal — Chrome rejects IP addresses as an RP ID).
function rpId() {
    return window.location.hostname;
}

function getStoredCredId() {
    try {
        return localStorage.getItem(CRED_KEY);
    } catch {
        return null;
    }
}

function storeCredId(id) {
    try {
        localStorage.setItem(CRED_KEY, id);
    } catch {
        /* ignore */
    }
}

export async function isSupported() {
    if (typeof window === 'undefined' || !window.PublicKeyCredential) return false;
    try {
        return await window.PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable();
    } catch {
        return false;
    }
}

async function register() {
    const cred = await navigator.credentials.create({
        publicKey: {
            challenge: randomChallenge(),
            rp: { name: 'F.R.I.D.A.Y.', id: rpId() },
            user: {
                id: new TextEncoder().encode('friday-owner'),
                name: 'owner',
                displayName: 'FRIDAY Owner',
            },
            pubKeyCredParams: [
                { type: 'public-key', alg: -7 }, // ES256
                { type: 'public-key', alg: -257 }, // RS256
            ],
            authenticatorSelection: {
                authenticatorAttachment: 'platform',
                userVerification: 'required',
                residentKey: 'preferred',
            },
            timeout: 60000,
            attestation: 'none',
        },
    });
    storeCredId(bufToBase64url(cred.rawId));
    return true;
}

async function authenticate() {
    const stored = getStoredCredId();
    if (!stored) throw new Error('NO_CREDENTIAL');
    await navigator.credentials.get({
        publicKey: {
            challenge: randomChallenge(),
            rpId: rpId(),
            allowCredentials: [{ type: 'public-key', id: base64urlToBuf(stored) }],
            userVerification: 'required',
            timeout: 60000,
        },
    });
    return true;
}

// High-level helper: first use registers the fingerprint, then authenticates.
// Subsequent uses just authenticate. Returns { ok, error?, reason? }.
export async function unlockWithFingerprint() {
    // WebAuthn needs a secure context AND a registrable RP ID. localhost is the
    // only origin browsers accept as an RP ID here — 127.0.0.1 / LAN IPs are
    // rejected, so bail early with a clear reason instead of crashing.
    if (typeof window === 'undefined' || !window.isSecureContext) {
        return { ok: false, reason: 'insecure' };
    }
    const host = window.location.hostname;
    if (host !== 'localhost' && !host.endsWith('.localhost')) {
        return { ok: false, reason: 'use-localhost' };
    }
    if (!(await isSupported())) {
        return { ok: false, reason: 'unsupported' };
    }
    try {
        if (!getStoredCredId()) {
            await register();
        }
        await authenticate();
        return { ok: true };
    } catch (err) {
        const name = err && err.name;
        if (name === 'NotAllowedError') return { ok: false, reason: 'cancelled' };
        if (name === 'InvalidStateError') return { ok: false, reason: 'unsupported' };
        return { ok: false, reason: 'error', error: err && err.message };
    }
}
