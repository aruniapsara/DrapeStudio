/**
 * DrapeStudio Service Worker
 * Strategy:
 *   - API routes (/v1/*): Network-first, no cache
 *   - Static assets (/static/*): Cache-first
 *   - Pages: Network-first with offline fallback
 */

'use strict';

const CACHE_NAME   = 'drapestudio-v2-shell';
const OFFLINE_URL  = '/';

const STATIC_PRECACHE = [
    '/static/css/style.css',
    '/static/css/tailwind-overrides.css',
    '/static/js/components.js',
    '/static/js/upload.js',
];

// ── Install ───────────────────────────────────────────────────────────────────
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(STATIC_PRECACHE).catch(() => {
                // If any asset fails, don't block install
            });
        })
    );
    self.skipWaiting();
});

// ── Activate ──────────────────────────────────────────────────────────────────
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(
                keys
                    .filter((key) => key !== CACHE_NAME)
                    .map((key) => caches.delete(key))
            )
        )
    );
    self.clients.claim();
});

// ── Fetch ─────────────────────────────────────────────────────────────────────
self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);

    // Skip non-GET and cross-origin requests
    if (event.request.method !== 'GET') return;
    if (url.origin !== self.location.origin) return;

    // API routes: network only (never cache)
    if (url.pathname.startsWith('/v1/')) {
        event.respondWith(fetch(event.request));
        return;
    }

    // Static assets: cache-first
    if (url.pathname.startsWith('/static/')) {
        event.respondWith(
            caches.match(event.request).then((cached) => {
                if (cached) return cached;
                return fetch(event.request).then((response) => {
                    if (response && response.status === 200) {
                        const clone = response.clone();
                        caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
                    }
                    return response;
                });
            })
        );
        return;
    }

    // Pages: network-first with offline fallback
    event.respondWith(
        fetch(event.request).catch(() => {
            return caches.match(event.request).then((cached) => {
                return cached || caches.match(OFFLINE_URL);
            });
        })
    );
});
