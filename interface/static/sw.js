/* DEEP service worker — installable PWA shell + offline fallback.
   Live data (/api, /ws, /debug, /voice) is always network-only so the app stays real-time.
   Shell assets are NETWORK-FIRST so UI updates always show when online; the cache is
   only a fallback for offline use. Bump CACHE on any shell change to purge old entries. */
const CACHE = 'deep-v92';
/* Only paths that actually exist. This list previously named /ai and a
   static/css + static/js tree that no longer ship: addAll() rejects wholesale
   if any single entry 404s, and the .catch below swallowed it, so the install
   step silently cached nothing at all and the offline fallback could never
   hit. The app's own assets are content-hashed, so they are not listed —
   the network-first handler caches them as they are fetched. */
const SHELL = [
  '/app',
  '/static/manifest.webmanifest',
  '/static/icons/icon-192.png', '/static/icons/icon-512.png'
];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL).catch(() => {})));
  self.skipWaiting();
});

self.addEventListener('activate', (e) => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))));
  self.clients.claim();
});

self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);
  // Never intercept live/real-time endpoints.
  if (e.request.method !== 'GET' ||
      url.pathname.startsWith('/api') ||
      url.pathname.startsWith('/ws') ||
      url.pathname.startsWith('/debug') ||
      url.pathname.startsWith('/voice')) return;

  // Everything else (app navigation + static shell): NETWORK-FIRST.
  // Fresh content whenever online; cached copy only as an offline fallback.
  e.respondWith(
    fetch(e.request).then(resp => {
      const copy = resp.clone();
      caches.open(CACHE).then(c => c.put(e.request, copy)).catch(() => {});
      return resp;
    }).catch(() =>
      caches.match(e.request).then(cached => cached || caches.match('/app'))
    )
  );
});
