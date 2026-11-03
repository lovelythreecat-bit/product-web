const task = await taskSpace('Feima auth implementation 2026-10-30');
const page = task.page('p1');
console.log({spaceId:task.spaceId,url:await page.url()});
console.log(await page.snapshot());
