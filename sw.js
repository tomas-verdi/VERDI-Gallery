const CACHE = 'verdi-v16';
const ASSETS = ['/'];

self.addEventListener('install', e => {
  self.skipWaiting();
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)));
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

const VIDEO_RE = /\.(mp4|mov)(\?.*)?$/i;

self.addEventListener('fetch', e => {
  // Videos: directo desde la red, sin cachear
  if (VIDEO_RE.test(e.request.url)) {
    e.respondWith(fetch(e.request));
    return;
  }
  // Todo lo demás: network-first con fallback a cache
  e.respondWith(
    fetch(e.request).then(res => {
      const clone = res.clone();
      caches.open(CACHE).then(c => c.put(e.request, clone));
      return res;
    }).catch(() => caches.match(e.request))
  );
});