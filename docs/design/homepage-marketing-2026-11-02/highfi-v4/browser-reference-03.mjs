const task=await taskSpace(15); const page=task.page('p1');
await page.mouse.move(1120,570,{label:'focus parallax demo viewport'});
await page.mouse.wheel(0,700,{label:'observe tilted gallery unfolding'});
console.log({shot:await page.screenshot()});
console.log(await page.evaluate(()=>({scrollY,transforms:[...document.querySelectorAll('[style*="transform"]')].slice(0,5).map(e=>getComputedStyle(e).transform)})));
