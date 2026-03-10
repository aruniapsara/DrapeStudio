/**
 * DrapeStudio Service Worker v2.1
 * Strategies: cache-first (static), network-first (API + HTML), offline fallback
 */

const CACHE_VERSION = 'v2.1';
const STATIC_CACHE  = `drapestudio-static-${CACHE_VERSION}`;
const DYNAMIC_CACHE = `drapestudio-dynamic-${CACHE_VERSION}`;
const API_CACHE     = `drapestudio-api-${CACHE_VERSION}`;

const STATIC_ASSETS = [
  '/',
  '/static/css/style.css',
  '/static/css/tailwind-overrides.css',
  '/static/js/components.js',
  '/static/logo.png',
  '/offline.html',
];

// ── Install: pre-cache static shell ──────────────────────────────────────────
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then(cache => cache.addAll(STATIC_ASSETS).catch(() => {}))
      .then(() => self.skipWaiting())
  );
});

// ── Activate: purge old caches ────────────────────────────────────────────────
self.addEventListener('activate', event => {
  const CURRENT = [STATIC_CACHE, DYNAMIC_CACHE, API_CACHE];
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(
        keys.filter(k => !CURRENT.includes(k)).map(k => caches.delete(k))
      ))
      .then(() => self.clients.claim())
  );
});

// ── Fetch: tiered caching strategy ───────────────────────────────────────────
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  // Only handle same-origin GET requests
  if (event.request.method !== 'GET' || url.origin !== self.location.origin) return;

  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/v1/')) {
    // Network-first for API calls, cache as fallback
    event.respondWith(
      fetch(event.request)
        .then(response => {
          if (response.ok) {
            const clone = response.clone();
            caches.open(API_CACHE).then(cache => cache.put(event.request, clone));
          }
          return response;
        })
        .catch(() => caches.match(event.request))
    );
  } else if (url.pathname.startsWith('/static/')) {
    // Cache-first for static assets
    event.respondWith(
      caches.match(event.request)
        .then(cached => cached || fetch(event.request).then(response => {
          if (response && response.status === 200) {
            const clone = response.clone();
            caches.open(STATIC_CACHE).then(cache => cache.put(event.request, clone));
          }
          return response;
        }))
    );
  } else {
    // Network-first for HTML pages, fallback to offline page
    event.respondWith(
      fetch(event.request)
        .catch(() => caches.match('/offline.html'))
    );
  }
});

// ── Push notifications ────────────────────────────────────────────────────────
self.addEventListener('push', event => {
  const data = event.data ? event.data.json() : {};
  const title = data.title || 'DrapeStudio';
  const options = {
    body: data.body || 'Your images are ready!',
    icon: '/static/icon-192.png',
    badge: '/static/icon-72.png',
    data: { url: data.url || '/' },
    actions: [
      { action: 'view',    title: 'View Images' },
      { action: 'dismiss', title: 'Dismiss'     },
    ],
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  if (event.action === 'view' || !event.action) {
    event.waitUntil(clients.openWindow(event.notification.data.url));
  }
});

// ── Background sync (offline upload queue) ────────────────────────────────────
self.addEventListener('sync', event => {
  if (event.tag === 'sync-uploads') {
    event.waitUntil(syncPendingUploads());
  }
});

async function syncPendingUploads() {
  const cache = await caches.open(DYNAMIC_CACHE);
  const keys = await cache.keys();
  const pending = keys.filter(k => k.url.includes('/offline-queue/'));
  for (const req of pending) {
    try {
      await fetch(req);
      await cache.delete(req);
    } catch (_) {
      // Will retry on next sync
    }
  }
}
