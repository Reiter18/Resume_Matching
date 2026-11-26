import { expect, test } from '@playwright/test'
import { PASSWORD, password, register } from './helpers.js'

test('регистрация, выход и повторный вход', async ({ page }) => {
  const email = await register(page)
  await page.getByRole('button', { name: 'Выйти' }).click()
  await expect(page.getByRole('button', { name: 'Войти' })).toBeVisible()

  await page.getByLabel('Email').fill(email)
  await password(page).fill(PASSWORD)
  await page.getByRole('button', { name: 'Войти' }).click()
  await expect(page.getByRole('heading', { name: 'Лента вакансий' })).toBeVisible()
})

test('без входа закрытые страницы ведут на форму входа, неверный пароль даёт ошибку', async ({ page }) => {
  await page.goto('/profile')
  await expect(page).toHaveURL(/\/login/)

  await page.getByLabel('Email').fill('nobody@example.com')
  await password(page).fill('wrong-password')
  await page.getByRole('button', { name: 'Войти' }).click()
  await expect(page.getByRole('alert')).toBeVisible()
})
