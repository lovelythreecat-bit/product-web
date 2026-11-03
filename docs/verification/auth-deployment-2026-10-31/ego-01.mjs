const task=await taskSpace('Feima auth deployment 2026-10-31');
const page=task.page('p1');
console.log({spaceId:task.spaceId});
await page.goto('http://43.142.150.158/login');
await page.waitForSelector('.app-header');
console.log(await page.snapshot());
