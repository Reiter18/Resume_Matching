import { expect } from '@playwright/test'

export const PASSWORD = 'e2e-password-123'
export const RESUME = 'Backend developer, 3 years of experience. Python, Django, FastAPI, PostgreSQL, Docker, Git, Linux.'

export const uniqueEmail = () => `e2e-${Date.now()}-${Math.floor(Math.random() * 1e6)}@example.com`
export const password = (page) => page.getByLabel('Пароль', { exact: true })

export async function register(page, email = uniqueEmail()) {
  await page.goto('/login')
  await page.getByRole('button', { name: 'Регистрация' }).click()
  await page.getByLabel('Email').fill(email)
  await password(page).fill(PASSWORD)
  await page.getByRole('button', { name: 'Создать аккаунт' }).click()
  await expect(page.getByRole('heading', { name: 'Лента вакансий' })).toBeVisible()
  return email
}

export async function pasteResume(page) {
  await page.goto('/profile')
  await page.getByRole('button', { name: 'Вставить текстом' }).click()
  await page.getByLabel('Текст резюме').fill(RESUME)
  await page.getByRole('button', { name: 'Сохранить текст' }).click()
  await expect(page.getByLabel('Ключевые слова резюме')).toContainText('python')
}
