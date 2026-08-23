/* DEEP service worker — installable PWA shell + offline fallback.
   Live data (/api, /ws, /debug, /voice) is always network-only so the app stays real-time.
   Shell assets are NETWORK-FIRST so UI updates always show when online; the cache is
   only a fallback for offline use. Bump CACHE on any shell change to purge old entries. */
const CACHE = 'deep-v92';

/* The navigable shell plus the assets that never change name. Everything else
   the app loads is hashed by the build, so it cannot be listed here — the
   network-first handler below caches those on first fetch, which is what makes
   the second visit work offline.

   This list used to name the legacy UI at /ai and five of its stylesheets and
   scripts. All six are gone: /ai is no longer a route, and static/css/ and
   static/js/ went with the legacy UI. addAll is atomic, so one 404 discarded
   the whole precache — and the .catch below swallowed the rejection, leaving an
   empty cache and no offline capability whatsoever.

   Two things this file cannot fix on its own, both outside the change that
   found it: nothing in the app calls navigator.serviceWorker.register(), so
   this worker is currently dormant; and /manifest.webmanifest and /sw.js are
   listed in the server's _PUBLIC_PATHS but served only under /static, so they
   404 at the root a service worker would need. Neither is precached here,
   because precaching a 404 is what caused the problem above. */
const SHELL = [
  '/', '/app',
  '/static/icons/icon-192.png', '/static/icons/icon-512.png'
];

self.addEventListener('install', (e) => {
  // One entry at a time, not addAll: a single missing asset must cost that
  // asset, not the entire shell. Failures are logged rather than swallowed,
  // because a silent empty cache is how the above went unnoticed.
  e.waitUntil(caches.open(CACHE).then(c => Promise.all(
    SHELL.map(url => c.add(url).catch(err =>
      console.warn('[sw] could not precache', url, err)
    ))
  )));
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
      // The shell is a fallback for *navigations* only. Handing index.html to an
      // uncached script or stylesheet request is worse than the network error it
      // replaces: the browser gets text/html where it asked for JavaScript, and
      // fails on a syntax error instead of an offline one.
      caches.match(e.request).then(cached =>
        cached || (e.request.mode === 'navigate' ? caches.match('/') : undefined)
      )
    )
  );
});
