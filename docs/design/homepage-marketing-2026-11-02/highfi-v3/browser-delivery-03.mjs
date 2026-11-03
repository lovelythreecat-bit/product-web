const task = await taskSpace('feima-v3-exhibition-20261102');
console.log({spaceId: task.spaceId});
const page = task.page('p1');
const base = 'file:///F:/Work/%E7%94%B5%E5%95%86/web/docs/design/homepage-marketing-2026-11-02/highfi-v3/';
await page.goto(base + 'gallery.html');
const gallery = await page.evaluate(async () => {
  await Promise.all([...document.images].map(i => {i.loading='eager'; return i.decode().catch(()=>null);}));
  return {title:document.title, images:document.images.length, brokenImages:[...document.images].filter(i=>!i.naturalWidth).map(i=>i.src)};
});
console.log({gallery});
await page.goto(base + 'index.html?theme=dark');
console.log(await page.snapshot());
await task.finish({keep:['p1']});
