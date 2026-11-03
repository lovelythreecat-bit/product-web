const task=await taskSpace(15);const page=task.page('p1');
console.log({current:await page.url()});
await page.goto('http://127.0.0.1:18114/highfi-v4/');
await page.waitForFunction(()=>!!window.exhibitionDiagnostics,undefined,{timeout:15000});
console.log(await page.evaluate(()=>({diagnostics:window.exhibitionDiagnostics,width:innerWidth,scrollWidth:document.documentElement.scrollWidth,missingImages:[...document.images].filter(i=>!i.naturalWidth).map(i=>i.src)})));
console.log({shot:await page.screenshot()});
