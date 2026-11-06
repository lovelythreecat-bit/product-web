const task=await taskSpace(36),page=task.page('p1');
console.log(await page.evaluate(()=>({width:innerWidth,height:innerHeight,scrollY,button:document.querySelector('#mode-pro').getBoundingClientRect().toJSON()})));
await page.evaluate(()=>document.querySelector('#mode-pro').scrollIntoView({behavior:'instant',block:'center'}));
console.log(await page.snapshot());
