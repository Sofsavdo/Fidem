const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = process.env.PORT || 3000;
const net = require('net');

// Optional same-origin API proxy. When BACKEND_INTERNAL_URL is set (e.g.
// http://fidem-backend.railway.internal:8001) every /api request - including
// the WebSocket upgrade - is forwarded to the backend, so the browser talks
// to ONE origin: no CORS preflight round trip before each new API URL.
// Unset = previous behaviour (static files only).
let BACKEND = null;
try {
  if (process.env.BACKEND_INTERNAL_URL) BACKEND = new URL(process.env.BACKEND_INTERNAL_URL);
} catch (e) {
  console.error('Invalid BACKEND_INTERNAL_URL, proxy disabled:', e.message);
}
const isApi = (url) => url === '/api' || url.startsWith('/api/') || url.startsWith('/api?');

function proxyHttp(req, res) {
  const secure = BACKEND.protocol === 'https:';
  const lib = secure ? require('https') : http;
  const headers = { ...req.headers, host: BACKEND.host };
  const up = lib.request({
    protocol: BACKEND.protocol,
    hostname: BACKEND.hostname,
    port: BACKEND.port || (secure ? 443 : 80),
    method: req.method,
    path: req.url,
    headers,
  }, (ur) => {
    res.writeHead(ur.statusCode, ur.headers);
    ur.pipe(res);
  });
  up.on('error', (e) => {
    console.error(`[proxy] ${req.method} ${req.url.split('?')[0]} -> ${BACKEND.host}: ${e.code || ''} ${e.message}`);
    if (!res.headersSent) res.writeHead(502, { 'Content-Type': 'application/json' });
    res.end('{"detail":"upstream unavailable"}');
  });
  req.pipe(up);
}

function proxyUpgrade(req, socket, head) {
  const secure = BACKEND.protocol === 'https:';
  const port = Number(BACKEND.port || (secure ? 443 : 80));
  const onConnect = () => {
    const lines = [`${req.method} ${req.url} HTTP/1.1`, `Host: ${BACKEND.host}`];
    for (const [k, v] of Object.entries(req.headers)) {
      if (k.toLowerCase() !== 'host') lines.push(`${k}: ${v}`);
    }
    up.write(lines.join('\r\n') + '\r\n\r\n');
    if (head && head.length) up.write(head);
    socket.pipe(up).pipe(socket);
  };
  const up = secure
    ? require('tls').connect({ host: BACKEND.hostname, port, servername: BACKEND.hostname }, onConnect)
    : net.connect(port, BACKEND.hostname, onConnect);
  up.on('error', (e) => {
    console.error(`[proxy] websocket -> ${BACKEND.host}: ${e.code || ''} ${e.message}`);
    socket.destroy();
  });
  socket.on('error', () => up.destroy());
}

const mimeTypes = {
  '.html': 'text/html',
  '.js': 'text/javascript',
  '.css': 'text/css',
  '.json': 'application/json',
  '.png': 'image/png',
  '.jpg': 'image/jpg',
  '.gif': 'image/gif',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.ttf': 'font/ttf',
  '.eot': 'application/vnd.ms-fontobject',
};

const server = http.createServer((req, res) => {
  if (BACKEND && isApi(req.url)) return proxyHttp(req, res);

  // Remove query string
  const urlPath = req.url.split('?')[0];
  
  // Default to index.html for SPA
  let filePath = path.join(BUILD_DIR, urlPath === '/' ? 'index.html' : urlPath);
  // Never serve anything outside the build directory (../ traversal).
  if (!path.resolve(filePath).startsWith(BUILD_DIR)) {
    res.writeHead(403);
    res.end('Forbidden');
    return;
  }
  
  // Check if file exists
  fs.access(filePath, fs.constants.F_OK, (err) => {
    if (err) {
      // File not found, serve index.html for SPA routing
      filePath = path.join(BUILD_DIR, 'index.html');
    }
    
    const extname = path.extname(filePath);
    const contentType = mimeTypes[extname] || 'application/octet-stream';
    
    // Cache headers
    let cacheControl = 'public, max-age=31536000, immutable'; // 1 year for static assets
    if (filePath.endsWith('index.html')) {
      cacheControl = 'no-cache, no-store, must-revalidate'; // Never cache HTML
    }
    
    // Get file stats for ETag
    fs.stat(filePath, (statErr, stats) => {
      if (statErr) {
        res.writeHead(500);
        res.end('Server Error');
        return;
      }
      
      const etag = `"${stats.mtime.getTime()}"`;
      
      // Check if client has cached version
      const ifNoneMatch = req.headers['if-none-match'];
      if (ifNoneMatch === etag) {
        res.writeHead(304, { 'ETag': etag });
        res.end();
        return;
      }
      
      fs.readFile(filePath, (readErr, content) => {
        if (readErr) {
          res.writeHead(500);
          res.end('Server Error');
          return;
        }
        
        res.writeHead(200, { 
          'Content-Type': contentType,
          'Cache-Control': cacheControl,
          'ETag': etag
        });
        res.end(content);
      });
    });
  });
});

server.on('upgrade', (req, socket, head) => {
  if (BACKEND && isApi(req.url)) return proxyUpgrade(req, socket, head);
  socket.destroy();
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(`Server running on http://0.0.0.0:${PORT}`);
});
