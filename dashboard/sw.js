// Service worker Silence Dashboard — réseau d'abord, cache en repli (offline shell).
const CACHE = 'silence-v1';
const ASSETS = [
  '/', '/index.html', '/mqtt.min.js', '/rambo-silence.png',
  '/manifest.json', '/icon-192.png', '/icon-512.png', '/apple-touch-icon.png'
];

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(ASSETS)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  // Données live (trips.json) : toujours réseau, jamais servies depuis le cache.
  if (url.pathname.startsWith('/data/')) return;
  e.respondWith(
    fetch(req)
      .then((resp) => {
        const copy = resp.clone();
        caches.open(CACHE).then((c) => c.put(req, copy)).catch(() => {});
        return resp;
      })
      .catch(() => caches.match(req).then((m) => m || caches.match('/index.html')))
  );
});
