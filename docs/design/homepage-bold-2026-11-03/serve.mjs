import {createServer} from 'node:http';
import {readFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const root=fileURLToPath(new URL('.',import.meta.url));
const types={'.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8','.js':'text/javascript; charset=utf-8','.png':'image/png','.webp':'image/webp'};
createServer(async(req,res)=>{
  try {
    const relative=decodeURIComponent(new URL(req.url,'http://localhost').pathname).replace(/^\/+/, '') || 'index.html';
    const file=path.resolve(root,relative);
    if(!file.startsWith(root) || !(relative === 'index.html' || relative === 'style.css' || relative === 'motion.js' || /^assets\/[\w.-]+\.(png|webp)$/.test(relative))) {res.writeHead(404).end();return;}
    const data=await readFile(file);res.writeHead(200,{'Content-Type':types[path.extname(file)] || 'application/octet-stream','Cache-Control':'no-store'});res.end(data);
  } catch {res.writeHead(404).end();}
}).listen(15213,'127.0.0.1',()=>console.log('Preview: http://127.0.0.1:15213'));
