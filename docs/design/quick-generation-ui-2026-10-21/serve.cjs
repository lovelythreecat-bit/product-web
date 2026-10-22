const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const root = __dirname;
const shared = path.resolve(root, '../quick-generation-2026-10-18/assets');
const types={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.png':'image/png','.svg':'image/svg+xml'};
http.createServer((req,res)=>{
  if(req.method!=='GET'&&req.method!=='HEAD'){res.writeHead(405);return res.end()}
  let pathname;try{pathname=decodeURIComponent(new URL(req.url,'http://localhost').pathname)}catch{res.writeHead(400);return res.end()}
  let file=pathname.startsWith('/quick-generation-2026-10-18/assets/')?path.join(shared,path.basename(pathname)):path.join(root,pathname==='/'?'index.html':pathname);
  const valid=file===root||file.startsWith(root+path.sep)||file.startsWith(shared+path.sep);
  if(!valid){res.writeHead(403);return res.end()}
  fs.readFile(file,(error,data)=>{if(error){res.writeHead(404);return res.end('Not found')}res.writeHead(200,{'Content-Type':types[path.extname(file)]||'application/octet-stream','Cache-Control':'no-store'});res.end(req.method==='HEAD'?undefined:data)});
}).listen(15181,'127.0.0.1',()=>console.log('Design preview: http://127.0.0.1:15181/'));
