const task = await taskSpace('feima-v4-spatial-story-20261103');
console.log({spaceId:task.spaceId});
const page = task.page('p1');
await page.goto('https://lusion.co/');
console.log(await page.snapshot());
console.log({shot:await page.screenshot()});
