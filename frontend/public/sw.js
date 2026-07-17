// FIDEM Service Worker — minimal offline-first cache
//
// Static JS/CSS build files are content-hashed (main.<hash>.js) - a given
// hash's content can never change, so cache-first for them is both correct
// and the fastest possible answer; there is nothing to "revalidate" (an
// earlier revision of this file tried stale-while-revalidate here, which
// just added a redundant background fetch for every asset on every load
// for no freshness benefit - real cost on slow mobile connections, so it
// was reverted). The one file whose content DOES change between deploys
// without its URL changing is index.html, and that already goes through
// the network-first `navigate` branch below.
//
// The actual fix for a long-lived Telegram Mini App WebView running an
// old build (it can keep the page's JS context alive across re-opens
// without ever triggering a fresh `navigate` fetch) lives in index.js:
// registration.update() on visibilitychange, and a reload once a new
// worker takes control.
const CACHE_NAME = 'fidem-v2';
const PRECACHE_URLS = [
  '/',
  '/manifest.json',
  '/favicon.ico',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE_URLS)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(
      keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))
    )).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  // Only handle GET
  if (request.method !== 'GET') return;
  const url = new URL(request.url);
  // Skip API + WS
  if (url.pathname.startsWith('/api') || url.pathname.startsWith('/ws') || url.protocol === 'ws:' || url.protocol === 'wss:') return;
  // Network-first for navigation; cache fallback
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request).then((res) => {
        const copy = res.clone();
        caches.open(CACHE_NAME).then((c) => c.put(request, copy));
        return res;
      }).catch(() => caches.match(request).then((m) => m || caches.match('/')))
    );
    return;
  }
  // Cache-first for static assets (see the note above on why these never
  // need revalidation).
  event.respondWith(
    caches.match(request).then((cached) => cached || fetch(request).then((res) => {
      if (res && res.status === 200 && res.type === 'basic') {
        const copy = res.clone();
        caches.open(CACHE_NAME).then((c) => c.put(request, copy));
      }
      return res;
    }).catch(() => cached))
  );
});

// Push notifications (future-proof; backend can send via web-push)
self.addEventListener('push', (event) => {
  if (!event.data) return;
  try {
    const data = event.data.json();
    event.waitUntil(
      self.registration.showNotification(data.title || 'FIDEM', {
        body: data.body || '',
        icon: '/logo192.png',
        badge: '/logo192.png',
        data: data.link || '/',
      })
    );
  } catch (e) {}
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const link = event.notification.data || '/';
  event.waitUntil(
    clients.matchAll({ type: 'window' }).then((cs) => {
      const existing = cs.find((c) => c.url.includes(self.location.origin));
      if (existing) { existing.focus(); existing.navigate(link); return; }
      return clients.openWindow(link);
    })
  );
});
