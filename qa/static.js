const http=require('http'),fs=require('fs'),path=require('path');
const D=process.env.QA_BUILD || (__dirname + '/../frontend/build');
const mt={'.html':'text/html','.js':'text/javascript','.css':'text/css','.json':'application/json','.svg':'image/svg+xml','.png':'image/png','.ico':'image/x-icon','.woff2':'font/woff2'};
http.createServer((q,r)=>{let u=q.url.split('?')[0];let f=path.join(D,u==='/'?'index.html':u);if(!f.startsWith(D)||!fs.existsSync(f)||fs.statSync(f).isDirectory())f=path.join(D,'index.html');
r.writeHead(200,{'Content-Type':mt[path.extname(f)]||'application/octet-stream','Cache-Control':'no-store'});fs.createReadStream(f).pipe(r)}).listen(18101,'127.0.0.1');
