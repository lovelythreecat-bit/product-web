import { expect, test } from '@playwright/test'

test('development shell loads without runtime errors or horizontal overflow', async ({ page }, testInfo) => {
  const errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  await page.goto('/')
  await expect(page.getByRole('heading', { name: '创作工作台' })).toBeVisible()
  await expect(page.getByText('TEST_ONLY · 开发环境')).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  expect(errors).toEqual([])
  await page.screenshot({ path: testInfo.outputPath('bootstrap.png'), fullPage: true })
})
