const task = await taskSpace('飞马首页 Oil 设计预览 20261103');
const page = task.page('p1');
await page.goto('file:///F:/Work/电商/web/docs/design/homepage-photo-v3-2026-11-03/index.html');
console.log({spaceId:task.spaceId});
console.log(await page.snapshot());
