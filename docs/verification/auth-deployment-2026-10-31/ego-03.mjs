const task=await taskSpace(15);
const page=task.page('p1');
await page.screenshot({path:'F:/Work/电商/web/docs/verification/auth-deployment-2026-10-31/domain-filing-block.png'});
await task.finish({keep:[]});
