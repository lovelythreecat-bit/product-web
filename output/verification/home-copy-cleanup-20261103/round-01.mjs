const task = await taskSpace('home-copy-cleanup-20261103');
const page = task.page('p1');
await page.goto('http://127.0.0.1:15173');
console.log({ spaceId: task.spaceId });
console.log(await page.snapshot());
