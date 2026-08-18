/**
 * FRIDAY Presence Service Worker (Phase 2.5).
 *
 * Receives payload-free "tickle" Web Pushes from the backend, pulls the
 * pending approvals list, and shows a notification with Approve / Deny
 * (and Undo, when the pending item is an autonomy undo prompt) actions.
 * Clicking an action POSTs the decision back — approval-first works from
 * the lock screen.
 */

const PENDING_URL = '/api/presence/pending';
const DECISION_URL = '/api/presence/decision';

// In hosted/remote setups, same-origin rewrites handle proxying.
// When an owner session token is entered interactively, it is passed
// to this worker via postMessage (see services/presencePush.js).
let apiToken = '';

self.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'FRIDAY_TOKEN') {
        apiToken = event.data.token || '';
    }
});

// fetch() wrapper that always attaches the API token (same as the page's
// window.fetch wrapper in api/config.js).
function authedFetch(url, options = {}) {
    const headers = new Headers(options.headers || {});
    if (apiToken && !headers.has('X-FRIDAY-Token')) {
        headers.set('X-FRIDAY-Token', apiToken);
    }
    return fetch(url, { ...options, headers });
}

self.addEventListener('install', (event) => self.skipWaiting());
self.addEventListener('activate', (event) => event.waitUntil(self.clients.claim()));

self.addEventListener('push', (event) => {
    event.waitUntil((async () => {
        let pending = [];
        try {
            const res = await authedFetch(PENDING_URL);
            if (res.ok) pending = (await res.json()).pending || [];
        } catch (_) {}

        const item = pending[0];
        const title = item ? '🛡️ FRIDAY needs approval' : '⚡ FRIDAY';
        const body = item
            ? `${item.description}  (${item.capability})`
            : 'Something needs your attention on the dashboard.';
        const data = item ? { approval_token: item.approval_token } : {};
        const actions = item
            ? [{ action: 'approve', title: '✅ Approve' }, { action: 'deny', title: '❌ Deny' }]
            : [];

        await self.registration.showNotification(title, {
            body, data, actions, tag: 'friday-presence', renotify: true,
            icon: '/icon-192.png', badge: '/icon-192.png',
        });
    })());
});

self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    const token = event.notification.data && event.notification.data.approval_token;
    const action = event.action;

    event.waitUntil((async () => {
        if (token && (action === 'approve' || action === 'deny')) {
            try {
                await authedFetch(DECISION_URL, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ approval_token: token, decision: action }),
                });
            } catch (_) {}
            return;
        }
        // Default click (or non-decision action): focus the dashboard.
        const allClients = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
        if (allClients.length > 0) {
            await allClients[0].focus();
        } else if (self.clients.openWindow) {
            await self.clients.openWindow('/');
        }
    })());
});
