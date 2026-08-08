/**
 * Presence Push registration (Phase 2.5).
 *
 * Registers the service worker and, once the user has granted notification
 * permission, subscribes to Web Push and stores the subscription as a PWA
 * presence device (POST /api/presence/register). Never prompts for
 * notification permission on load — the HUD surfaces a one-tap enable
 * action when permission is 'default'.
 */

const SW_PATH = '/sw.js';

export async function registerPresenceWorker() {
    if (!('serviceWorker' in navigator)) return null;
    try {
        return await navigator.serviceWorker.register(SW_PATH);
    } catch (_) {
        return null;
    }
}

export async function subscribePresencePush() {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) return false;
    if (typeof Notification === 'undefined' || Notification.permission !== 'granted') return false;
    try {
        const reg = await navigator.serviceWorker.ready;
        const keyRes = await fetch('/api/presence/vapid-key');
        const { public_key } = keyRes.ok ? await keyRes.json() : {};
        if (!public_key) return false;                    // push not configured on backend

        let sub = await reg.pushManager.getSubscription();
        if (!sub) {
            sub = await reg.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: urlBase64ToUint8Array(public_key),
            });
        }
        const res = await fetch('/api/presence/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                device_kind: 'pwa',
                token: JSON.stringify(sub),
                label: 'Prem (this device)',
            }),
        });
        return res.ok;
    } catch (_) {
        return false;
    }
}

export function presencePermissionState() {
    if (typeof Notification === 'undefined') return 'unsupported';
    return Notification.permission;                       // 'granted' | 'denied' | 'default'
}

function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
    const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
    const raw = atob(base64);
    const arr = new Uint8Array(raw.length);
    for (let i = 0; i < raw.length; i++) arr[i] = raw.charCodeAt(i);
    return arr;
}
