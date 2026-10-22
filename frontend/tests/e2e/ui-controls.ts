import { expect, type Locator } from '@playwright/test'

/** Select through the visible Element Plus popup, retaining native fixture support. */
export async function selectOption(control: Locator, value: string) {
  if (await control.evaluate(element => element.tagName === 'SELECT')) {
    await control.selectOption(value)
    return
  }
  const choice = await control.evaluate((element, selected) => {
    const options = element.closest('.ui-select-field')?.querySelectorAll('select option')
    const entries = Array.from(options ?? []) as HTMLOptionElement[]
    const index = entries.findIndex(option => option.value === selected)
    if (index < 0) return null
    const label = entries[index].textContent?.trim()
    // Different values may legitimately share a label; preserve their popup order.
    const occurrence = entries.slice(0, index).filter(option => option.textContent?.trim() === label).length
    return { label, occurrence }
  }, value)
  if (!choice?.label) throw new Error('Option unavailable: ' + value)
  await control.locator('xpath=ancestor::div[contains(@class,"ui-select-field")][1]').locator('.el-select__wrapper').click()
  const listbox = await control.getAttribute('aria-controls')
  const popup = control.page().locator(`[id="${listbox}"]`)
  await popup.getByRole('option', { name: choice.label, exact: true }).nth(choice.occurrence).click()
  await expect(popup).not.toBeVisible()
}
