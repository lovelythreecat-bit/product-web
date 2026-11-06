const task = await taskSpace(33);
const page = task.page('p1');
for (const [width, height] of [[1440, 900], [390, 844]]) {
  await page.cdp('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile: false });
  for (const theme of ['light', 'dark']) {
    if (theme === 'dark') await page.click('loc=css:button[aria-label="切换深色主题"]');
    if (width === 1440) {
      await page.click('loc=href:/#lingling');
      await page.waitForFunction(() => Math.abs(document.querySelector('#lingling').getBoundingClientRect().top - 100) < 2, undefined, { timeout: 10000 });
    } else {
      await page.evaluate(() => window.scrollTo({ top: 1500, behavior: 'instant' }));
    }
    const result = await page.evaluate(() => {
      const header = document.querySelector('.site-home .nav').getBoundingClientRect();
      return { width: innerWidth, theme: document.querySelector('.site-home').dataset.theme, scrollY, top: header.top, bottom: header.bottom, overflow: document.documentElement.scrollWidth > innerWidth };
    });
    if (result.top !== 0 || result.overflow) throw new Error(JSON.stringify(result));
    console.log(result);
    await page.screenshot({ path: `F:/Work/电商/web/output/home-header-20261103/${width}-${theme}.png` });
  }
  await page.click('loc=css:button[aria-label="切换浅色主题"]');
  if (width === 1440) {
    console.log(await page.evaluate(() => {
      const section = document.querySelector('#creation');
      window.scrollTo({ top: section.getBoundingClientRect().top + scrollY + 300, behavior: 'instant' });
      const header = document.querySelector('.site-home .nav').getBoundingClientRect();
      const stage = document.querySelector('.creation-pin').getBoundingClientRect();
      if (stage.top < header.bottom) throw new Error('Creation stage is obscured');
      return { creationTop: stage.top, headerBottom: header.bottom };
    }));
  }
}
await task.finish({ keep: [] });
