const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = process.env.PORT || 3000;
const BUILD_DIR = path.join(__dirname, 'build');

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
  // Remove query string
  const urlPath = req.url.split('?')[0];
  
  // Default to index.html for SPA
  let filePath = path.join(BUILD_DIR, urlPath === '/' ? 'index.html' : urlPath);
  
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

server.listen(PORT, '0.0.0.0', () => {
  console.log(`Server running on http://0.0.0.0:${PORT}`);
});
