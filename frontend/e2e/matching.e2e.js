import { expect, test } from '@playwright/test'
import { pasteResume, register } from './helpers.js'

test('вкладки ленты: без резюме подсказка, все вакансии доступны', async ({ page }) => {
  await register(page)
  await expect(page.getByRole('tab', { name: 'Подходящие мне' })).toHaveAttribute('aria-selected', 'true')
  await expect(page.getByRole('alert')).toContainText('загрузите резюме')

  await page.getByRole('tab', { name: 'Все вакансии' }).click()
  await expect(page).toHaveURL(/show=all/)
  await expect(page.getByLabel('Поиск')).toBeVisible()
})

test('предпочтения сохраняются и переживают перезагрузку', async ({ page }) => {
  await register(page)
  await page.goto('/preferences')
  const format = page.getByRole('group', { name: 'Формат работы' })
  await format.getByLabel('Удалённо').check()
  await page.getByRole('button', { name: 'Сохранить' }).click()
  await expect(page.getByRole('status').filter({ hasText: 'Сохранено' })).toBeVisible()

  await page.reload()
  await expect(format.getByLabel('Удалённо')).toBeChecked()
})

test('резюме, подходящие вакансии и разбор оценки', async ({ page }) => {
  await register(page)
  await pasteResume(page)
  await page.goto('/')

  const card = page.getByRole('article').first()
  await expect(card.or(page.getByText(/Подходящих вакансий пока нет/))).toBeVisible({ timeout: 30_000 })
  test.skip((await page.getByRole('article').count()) === 0, 'в базе нет вакансий: выполните python -m app.cli arbeitnow 1')

  await card.getByRole('link').first().click()
  await expect(page).toHaveURL(/\/vacancies\/\d+/)
  await expect(page.getByRole('heading', { name: /^Почему \d+%$/ })).toBeVisible()
  await expect(page.getByRole('progressbar', { name: 'Навыки' })).toBeVisible()
})
