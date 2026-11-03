const task = await taskSpace(14);
const page = task.page('p1');
await page.goto('http://127.0.0.1:15173/login');
await page.waitForSelector('#auth-account');
console.log(await page.snapshot());
