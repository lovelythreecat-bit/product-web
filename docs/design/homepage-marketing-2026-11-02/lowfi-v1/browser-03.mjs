const task=await taskSpace(11);
const page=task.page('p1');
await page.goto('file:///F:/Work/%E7%94%B5%E5%95%86/web/docs/design/homepage-marketing-2026-11-02/lowfi-v1/index.html');
console.log(await page.evaluate(()=>({audit:window.COPY_AUDIT,modules:[...document.querySelectorAll('.module')].map(n=>({id:n.id,title:n.dataset.title,height:n.offsetHeight})),horizontalOverflow:document.documentElement.scrollWidth>innerWidth,brokenImages:[...document.images].filter(i=>i.complete&&!i.naturalWidth).map(i=>i.src)})));
console.log(await page.screenshot({path:'F:/Work/电商/web/docs/design/homepage-marketing-2026-11-02/lowfi-v1/screenshots/desktop-initial.png'}));
