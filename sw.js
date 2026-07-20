/* urth. order dashboard — service worker (push notifications only; no offline caching) */
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (e) => e.waitUntil(self.clients.claim()));

self.addEventListener('push', (e) => {
  let d = {};
  try { d = e.data ? e.data.json() : {}; }
  catch (_) { d = { title: 'urth · Order update', body: e.data ? e.data.text() : '' }; }
  const title = d.title || 'urth · Order update';
  const opts = {
    body: d.body || '',
    tag: d.tag || 'order',
    renotify: true,
    icon: 'assets/favicon-192.png',
    badge: 'assets/favicon-192.png',
    data: { url: d.url || '/' }
  };
  e.waitUntil(self.registration.showNotification(title, opts));
});

self.addEventListener('notificationclick', (e) => {
  e.notification.close();
  const url = (e.notification.data && e.notification.data.url) || '/';
  e.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((list) => {
      for (const c of list) { if ('focus' in c) return c.focus(); }
      if (self.clients.openWindow) return self.clients.openWindow(url);
    })
  );
});
