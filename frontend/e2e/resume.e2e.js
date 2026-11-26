import { expect, test } from '@playwright/test'
import { pasteResume, register } from './helpers.js'

test('резюме текстом: ключевые слова находятся, правятся и сохраняются', async ({ page }) => {
  await register(page)
  await pasteResume(page)

  const words = page.getByLabel('Ключевые слова резюме')
  await expect(words).toContainText('docker')
  await page.getByRole('button', { name: 'Удалить docker' }).click()
  await page.getByRole('button', { name: 'Сохранить слова' }).click()
  await expect(page.getByText('Сохранено').first()).toBeVisible()

  await page.reload()
  await expect(words).toContainText('python')
  await expect(words).not.toContainText('docker')
})
