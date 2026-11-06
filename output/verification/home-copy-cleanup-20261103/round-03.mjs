const task = await taskSpace(34);
const page = task.page('p1');
await page.click('button[aria-label="切换深色主题"]');
console.log(await page.evaluate(() => ({theme:document.querySelector('.site-home').dataset.theme, overflow:document.documentElement.scrollWidth > innerWidth, removed:[...document.querySelectorAll('.explore,.scroll-link,.lingling-link small,.story-steps > p')].length})));
console.log(await page.screenshot({path:'F:/Work/电商/web/output/home-copy-cleanup-20261103/mobile-dark.png'}));
await page.click('button[aria-label="切换浅色主题"]');
await task.finish({keep:[]});
