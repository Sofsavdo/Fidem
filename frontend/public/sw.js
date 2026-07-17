// FIDEM Service Worker — minimal offline-first cache
//
// v2: static assets are now stale-while-revalidate, not pure cache-first.
// Pure cache-first never re-checks the network once a URL is cached, which
// is fine for content-hashed JS/CSS chunks (a new deploy gets new hashed
// filenames, so old cache entries just go unused) - but Telegram's Mini
// App WebView often keeps a page's JS context alive across re-opens
// instead of doing a fresh top-level navigation, and can serve its OWN
// cached copy of index.html without ever re-hitting the network. When
// that happens, the page never learns new hashed filenames exist, and a
// long-lived session (exactly what a Telegram Mini App is, compared to a
// browser tab someone just opened) can keep running whatever JS bundle
// was current the day they first opened it - shipped features/fixes
// never reach that session until something forces a real reload.
// Stale-while-revalidate still answers instantly from cache, but always
// fires a background fetch to refresh the cache with whatever the
// network currently has, so the NEXT load (even without a full reload)
// picks up new files, and the update-detection wired up in index.js can
// prompt/force a reload once a new version is actually available.
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
  // Stale-while-revalidate for static assets: answer from cache instantly
  // if present, but always also fetch in the background and update the
  // cache - so a session that never fully reloads still converges on the
  // latest build within one round trip instead of staying stale forever.
  // event.waitUntil keeps the worker alive long enough for the background
  // fetch/cache.put to actually finish once respondWith has already
  // resolved with the cached copy - without it the browser is free to
  // suspend the worker mid-fetch and the revalidation silently never lands.
  event.respondWith(
    caches.open(CACHE_NAME).then(async (cache) => {
      const cached = await cache.match(request);
      const network = fetch(request).then((res) => {
        if (res && res.status === 200 && res.type === 'basic') {
          cache.put(request, res.clone());
        }
        return res;
      }).catch(() => null);
      if (cached) {
        event.waitUntil(network);
        return cached;
      }
      return (await network) || cached;
    })
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
