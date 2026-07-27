import { expect, test } from '@playwright/test'

test('voice debt record becomes traceable balance and overdue reminder', async ({ page }) => {
  await page.goto('/')
  await page.locator('[data-action="voice"]').click()
  await page.locator('[data-action="demo-audio"]').click()
  const lowConfidence = page.locator('[data-field="items.1.quantity"]')
  await expect(lowConfidence).toHaveClass(/is-low-confidence/)
  const quantity = lowConfidence.getByRole('spinbutton')
  await quantity.fill('3')
  await quantity.press('Tab')
  await page.locator('[data-action="confirm"]').click()

  await page.locator('[data-nav="query"]').click()
  await page.getByText('王老板还欠多少钱', { exact: true }).click()
  await expect(page.getByText('570.00', { exact: true }).first()).toBeVisible()
  await expect(page.getByRole('heading', { name: /当前欠款为/ })).toBeVisible()
  await expect(page.getByRole('region', { name: '关联凭证' })).toBeVisible()

  await page.goto('/')
  await expect(page.getByText('逾期提醒', { exact: true })).toBeVisible()
  await expect(page.getByText(/位客户存在逾期账目/)).toBeVisible()
})
