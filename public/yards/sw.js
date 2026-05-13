// Service Worker for Yard Signs PWA — offline photo queue
const CACHE_NAME = 'yards-v1';
const OFFLINE_QUEUE_KEY = 'yards-offline-queue';

self.addEventListener('install', e => { self.skipWaiting(); });
self.addEventListener('activate', e => { self.clients.claim(); });

// Cache basic assets
self.addEventListener('fetch', e => {
  if (e.request.method === 'GET') {
    e.respondWith(fetch(e.request).catch(() => caches.match(e.request)));
  }
});
