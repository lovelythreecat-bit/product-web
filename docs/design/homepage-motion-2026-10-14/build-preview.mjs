import fs from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { execFileSync } from 'node:child_process'
import { chromium } from '../../../frontend/node_modules/@playwright/test/index.mjs'

const dir = path.dirname(fileURLToPath(import.meta.url))
const root = path.resolve(dir, '../../..')
await fs.mkdir(path.join(dir, 'assets'), { recursive: true })
for (const name of ['commerce-hero-v3.png', 'commerce-categories-v3.png']) {
  await fs.copyFile(path.join(root, 'frontend/public/homepage', name), path.join(dir, 'assets', name))
}
const source = path.join(dir, 'assets/commerce-categories-v3.png')
execFileSync('ffmpeg', ['-hide_banner', '-loglevel', 'error', '-y', '-i', source, '-vf', 'crop=724:724:1448:0,scale=640:640', '-frames:v', '1', path.join(dir, 'assets/headphones-poster.jpg')])
const zoom = "crop=724:724:1448:0,scale=1448:1448,zoompan=z='1.03+0.065*(1-cos(2*PI*on/119))/2':x='iw/2-iw/zoom/2+12*sin(2*PI*on/119)':y='ih/2-ih/zoom/2':d=120:s=640x640:fps=25"
execFileSync('ffmpeg', ['-hide_banner', '-loglevel', 'error', '-y', '-i', source, '-vf', zoom, '-frames:v', '120', '-c:v', 'libx264', '-crf', '22', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-an', path.join(dir, 'assets/headphones-loop.mp4')])
const browser = await chromium.launch({ headless: true, channel: 'chrome' })
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } })
await page.goto('http://127.0.0.1:15173/', { waitUntil: 'networkidle' })
const html = await page.locator('.site-home').evaluate(el => {
  const copy = el.cloneNode(true)
  copy.querySelectorAll('img').forEach(img => img.setAttribute('src', img.getAttribute('src').replace('/homepage/', './assets/')))
  copy.querySelectorAll('a[href^="/"]').forEach(a => a.setAttribute('href', 'http://127.0.0.1:15173' + a.getAttribute('href')))
  copy.querySelectorAll('.home-load-error').forEach(el => el.remove())
  return copy.outerHTML
})
await browser.close()
const tokens = await fs.readFile(path.join(root, 'frontend/src/styles/tokens.css'), 'utf8')
const home = await fs.readFile(path.join(root, 'frontend/src/features/site/homepage.css'), 'utf8')
await fs.writeFile(path.join(dir, 'base.css'), tokens + '\n' + home)
await fs.writeFile(path.join(dir, 'index.html'), `<!doctype html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>首页动效预览 V1</title><link rel="stylesheet" href="./base.css"><link rel="stylesheet" href="./motion.css"></head><body><main id="main-content">${html}</main><aside class="preview-tools" aria-label="设计预览控制"><span>动效预览 V1</span><a href="#creation-video">看视频示例</a><button id="motion-toggle" type="button" aria-pressed="false">暂停动效</button><button id="motion-replay" type="button">重播首屏</button></aside><script src="./motion.js"></script></body></html>`)
console.log('Preview generated:', dir)
