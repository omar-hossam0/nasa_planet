// Dependency-free local server for the precomputed demo snapshot.
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');

const root = __dirname;
const mime = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8', '.png': 'image/png', '.svg': 'image/svg+xml', '.json': 'application/json' };
const server = http.createServer((request, response) => {
  const pathname = decodeURIComponent(new URL(request.url || '/', 'http://localhost').pathname);
  if (pathname.startsWith('/v1/') || pathname === '/health') {
    response.writeHead(503, { 'Content-Type': 'application/json' });
    response.end(JSON.stringify({ error: { code: 'OFFLINE', detail: 'The local demo uses precomputed data.' } }));
    return;
  }
  const name = pathname === '/' ? '/index.html' : pathname;
  const file = path.resolve(root, '.' + name);
  if (!file.startsWith(root + path.sep)) { response.writeHead(403); response.end(); return; }
  fs.readFile(file, (error, body) => {
    if (error) { response.writeHead(404); response.end('Not found'); return; }
    response.writeHead(200, { 'Content-Type': mime[path.extname(file)] || 'application/octet-stream', 'Cache-Control': 'no-store' });
    response.end(body);
  });
});
server.listen(4173, '127.0.0.1', () => console.log('AstraVerd offline demo: http://127.0.0.1:4173/'));
