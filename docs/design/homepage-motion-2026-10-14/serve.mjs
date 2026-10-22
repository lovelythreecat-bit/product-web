import http from 'node:http'
import fs from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
const root = path.dirname(fileURLToPath(import.meta.url))
const types = { '.html':'text/html; charset=utf-8', '.css':'text/css; charset=utf-8', '.js':'text/javascript; charset=utf-8', '.png':'image/png', '.jpg':'image/jpeg', '.mp4':'video/mp4' }
http.createServer(async (req,res) => {
  try {
    const file = path.resolve(root, '.' + decodeURIComponent(new URL(req.url,'http://localhost').pathname).replace(/\/$/, '/index.html'))
    if (!file.startsWith(root + path.sep)) { res.writeHead(403).end(); return }
    const data = await fs.readFile(file)
    res.writeHead(200, { 'Content-Type': types[path.extname(file)] || 'application/octet-stream', 'Content-Length': data.length, 'Cache-Control':'no-store' }).end(data)
  } catch { res.writeHead(404).end('Not found') }
}).listen(15174, '127.0.0.1', () => console.log('Motion preview: http://127.0.0.1:15174'))
