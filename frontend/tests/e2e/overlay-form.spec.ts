import { expect, test } from '@playwright/test'

test('parent form: built-in mouse and keyboard close never submits; explicit action does', async ({ page }, info) => {
  await page.goto('/tests/fixtures/overlays.html')
  const cases: {variant:string; purpose:string; location:string; activation:string; submits:number; open:string|null}[] = []
  for (const variant of ['dialog', 'drawer']) {
    await page.getByLabel('组合类型').selectOption(variant)
    for (const purpose of ['read', 'edit', 'charge', 'delete']) {
      await page.getByLabel('组合用途').selectOption(purpose)
      for (const location of ['header', 'footer']) {
        for (const activation of ['click', 'Enter', 'Space']) {
          await page.getByRole('button', {name:'打开父表单弹层'}).click()
          const dialog = page.getByRole('dialog', {name:'父表单组合'})
          await expect(dialog).toBeVisible()
          const button = location === 'header' ? dialog.locator('header button') : dialog.locator('footer').getByRole('button', {name:purpose === 'read' ? '关闭' : '取消', exact:true})
          if (activation === 'click') await button.click()
          else { await button.focus(); await button.press(activation) }
          await expect(dialog).not.toBeVisible()
          cases.push({variant, purpose, location, activation, submits:Number(await page.getByTestId('form-submits').textContent()), open:await page.getByTestId('form-open').textContent()})
        }
      }
    }
  }
  await info.attach('parent-form-cases', {body:JSON.stringify(cases,null,2),contentType:'application/json'})
  expect.soft(cases.filter(item => item.submits !== 0 || item.open !== 'false')).toEqual([])
  const beforeSubmit = Number(await page.getByTestId('form-submits').textContent())
  await page.getByRole('button', {name:'打开父表单弹层'}).click()
  await page.getByRole('button', {name:'明确提交'}).click()
  await expect(page.getByTestId('form-submits')).toHaveText(String(beforeSubmit + 1))
  await expect(page.getByRole('dialog', {name:'父表单组合'})).toBeVisible()
})
