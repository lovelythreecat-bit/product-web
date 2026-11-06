const task = await taskSpace(36);
const page = task.page('p2');
console.log(await page.snapshot());
await page.screenshot({path:'F:/Work/电商/web/docs/design/homepage-folder-2026-11-03/baseline.png'});
