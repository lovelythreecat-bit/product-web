const task=await taskSpace(36),page=task.page('p1');
console.log(await page.evaluate(()=>({width:innerWidth,height:innerHeight,scrollY,gsapTime:window.gsap?.globalTimeline.time(),opacity:getComputedStyle(document.querySelector('.folders')).opacity,loading:[...document.images].filter(i=>!i.complete).length})));
console.log(await page.snapshot());
