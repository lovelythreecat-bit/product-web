const task = await taskSpace(30);
const page = task.page('p1');
for (const [width, height] of [[1440, 900], [390, 844]]) {
  await page.cdp('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile: false });
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'instant' }));
  await page.click('loc=href:/ai-customer-service#guidance');
  await page.waitForFunction(() => {
    const section = document.querySelector('#guidance').getBoundingClientRect();
    const header = document.querySelector('.fairy-navigation').getBoundingClientRect();
    return window.scrollY > 500 && section.top >= header.bottom && section.top < header.bottom + 26;
  }, undefined, { timeout: 10000 });
  console.log(await page.evaluate(() => {
    const header = document.querySelector('.fairy-navigation').getBoundingClientRect();
    return { width: innerWidth, scrollY, headerTop: header.top, headerBottom: header.bottom, sectionTop: document.querySelector('#guidance').getBoundingClientRect().top, overflow: document.documentElement.scrollWidth > innerWidth };
  }));
  await page.screenshot({ path: `F:/Work/电商/web/output/support-header-20261103/${width}.png` });
}
await task.finish({ keep: [] });
