// Passphrase helpers for FRIDAY's lock screen onboarding.
//
// SECURITY NOTE (fixed): this file previously persisted the owner's unlock
// and lock phrases in plaintext `localStorage`, right next to the AES-GCM
// encrypted vault — anyone with devtools could read the passphrase and
// defeat the vault. The storage functions were removed; `normalize` remains
// as the shared normalization used when comparing typed/spoken phrases.

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
