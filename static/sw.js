const CACHE_NAME = 'tali-agent-v1';

// Keep this minimal: cache the shell so iOS "Add to Home Screen" opens fast.
const ASSETS = [
  '/static/live.html',
  '/static/manifest.webmanifest'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const { request } = event;

  // Network-first for API calls
  if (request.url.includes('/chat/') || request.url.includes('/general/') || request.url.includes('/customers')) {
    event.respondWith(
      fetch(request).catch(() => caches.match(request))
    );
    return;
  }

  // Cache-first for static shell
  event.respondWith(
    caches.match(request).then((cached) => cached || fetch(request))
  );
});
