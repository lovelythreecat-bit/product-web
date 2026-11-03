const task=await taskSpace(15); const page=task.page('p1');
await page.mouse.move(850,420,{label:'observe spatial pointer response'});
console.log({before:await page.screenshot()});
await page.mouse.wheel(0,760,{label:'explore scroll camera movement'});
console.log({after:await page.screenshot()});
await page.goto('https://ui.aceternity.com/live-preview/hero-parallax-demo');
console.log(await page.snapshot());
console.log({second:await page.screenshot()});
