import { expect, test } from '@playwright/test'

test('voice failure falls back to a confirmable manual record', async ({ page }) => {
  await page.route('**/api/v1/records/voice', route => route.abort('failed'))
  await page.goto('/#/pages/record-voice/index')
  await page.locator('[data-action="demo-audio"]').click()
  const fallback = page.locator('[data-action="manual-fallback"]')
  await expect(fallback).toBeVisible()
  await fallback.click()

  await page.getByRole('textbox').nth(0).fill('王老板')
  await page.getByRole('textbox').nth(1).fill('测试灯泡')
  await page.getByRole('spinbutton').nth(0).fill('1')
  await page.getByRole('spinbutton').nth(1).fill('25')
  await page.locator('uni-button').filter({ hasText: '生成确认单' }).click()
  await page.locator('[data-action="confirm"]').click()

  await expect(page.getByText('小店记', { exact: true }).first()).toBeVisible()
  await page.locator('[data-nav="query"]').click()
  await page.getByText('王老板还欠多少钱', { exact: true }).click()
  await expect(page.getByText('25.00', { exact: true }).first()).toBeVisible()
})
