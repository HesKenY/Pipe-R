const CACHE_NAME = 'cherp-v1.1.0';

const PRECACHE_URLS = [
  '/',
  '/index.html',
  '/manifest.json',
  '/core/ui/styles.css',
  '/core/roles/roles.js',
  '/core/ui/shell.js',
  '/core/module-loader.js',
  '/main.js',
  '/modules.config.json'
  // NOTE: config/instance.json and auth/supabase files are NOT precached (security)
];

self.addEventListener('install', event => {
  console.log('[SW] Installing:', CACHE_NAME);
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(PRECACHE_URLS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', event => {
  console.log('[SW] Activating:', CACHE_NAME);
  event.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys
          .filter(key => key !== CACHE_NAME)
          .map(key => {
            console.log('[SW] Removing old cache:', key);
            return caches.delete(key);
          })
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const { request } = event;

  // Skip non-GET and cross-origin requests for Supabase API calls
  if (request.method !== 'GET') return;

  const url = new URL(request.url);

  // Network-first for Supabase API and CDN resources
  if (url.hostname.includes('supabase') || url.hostname.includes('cdn.jsdelivr.net')) {
    event.respondWith(networkFirst(request));
    return;
  }

  // Cache-first for local app assets
  event.respondWith(cacheFirst(request));
});

async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;

  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, response.clone());
    }
    return response;
  } catch (err) {
    // If offline and not in cache, return a fallback
    if (request.destination === 'document') {
      const fallback = await caches.match('/index.html');
      if (fallback) return fallback;
    }
    return new Response('Offline — resource not cached.', {
      status: 503,
      statusText: 'Service Unavailable',
      headers: { 'Content-Type': 'text/plain' }
    });
  }
}

async function networkFirst(request) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, response.clone());
    }
    return response;
  } catch (err) {
    const cached = await caches.match(request);
    if (cached) return cached;
    return new Response(JSON.stringify({ error: 'Offline' }), {
      status: 503,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}
