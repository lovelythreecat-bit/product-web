import { expect, test } from '@playwright/test'

test('development shell loads without runtime errors or horizontal overflow', async ({ page }, testInfo) => {
  const errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  await page.goto('/')
  await expect(page.getByRole('heading', { name: '让好商品，亮眼登场。', exact: true })).toBeVisible()
  await expect(page.getByRole('link', { name: /注册体验/ }).first()).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  expect(errors).toEqual([])
  await page.screenshot({ path: testInfo.outputPath('bootstrap.png'), fullPage: true })
})
