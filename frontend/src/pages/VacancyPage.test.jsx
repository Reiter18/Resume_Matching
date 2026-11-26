import { screen } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { HEALTH, USER, mockApi, renderApp } from '../test/utils.jsx'

beforeEach(() => localStorage.setItem('jobmatch_token', 'valid'))
afterEach(() => {
  vi.unstubAllGlobals()
  localStorage.clear()
})

const detail = {
  id: 5, title: 'Python Backend', company: 'Acme', location: 'Berlin', work_format: 'hybrid', employment_types: ['full_time'],
  schedule: null, hours_per_week: null, experience_years_min: null, salary_min: null, salary_max: null, salary_currency: null,
  tags: [], skills: ['python', 'docker', 'kubernetes'], published_at: '2026-11-01T10:00:00Z', url: 'https://arbeitnow.example/5',
  source: 'arbeitnow', description_text: 'Пишем бэкенд на Python.\nУдалёнка возможна.', canonical_id: null,
  also_found_at: [{ source: 'other', url: 'https://other.example/5' }],
}  // prettier-ignore
const criteria = {
  skills: { score: 0.59, weight: 40, status: 'partial', text: 'совпало 2 из 3', matched: ['python', 'docker'], missing: ['kubernetes'] },
  work_format: { score: 0.5, weight: 15, status: 'partial', text: 'гибрид: рядом с желаемым форматом' },
  salary: { score: null, weight: 15, status: 'unknown', text: 'зарплата в вакансии не указана' },
}
const summary = {
  matches: ['навыки: python, docker'], gaps: ['не хватает навыков: kubernetes'], unknown: ['зарплата в вакансии не указана'],
}  // prettier-ignore
const setup = (match) =>
  mockApi({
    'GET /me': { status: 200, body: USER },
    'GET /health': { status: 200, body: HEALTH },
    'GET /vacancies/5': { status: 200, body: detail },
    'GET /matches/5': match,
  })

it('показывает вакансию и разбор оценки по критериям', async () => {
  setup({ status: 200, body: { vacancy: detail, score: 56, confidence: 80, hidden: false, criteria, summary } })
  renderApp('/vacancies/5')
  expect(await screen.findByRole('heading', { name: 'Python Backend' })).toBeInTheDocument()
  expect(screen.getByText(/Пишем бэкенд/)).toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'Открыть на arbeitnow' })).toHaveAttribute('href', 'https://arbeitnow.example/5')
  expect(screen.getByRole('link', { name: 'other' })).toHaveAttribute('href', 'https://other.example/5')

  expect(await screen.findByRole('heading', { name: 'Почему 56%' })).toBeInTheDocument()
  expect(screen.getByText(/Данные есть по 2 из 3 критериев/)).toBeInTheDocument()
  expect(screen.getByText(/80% важного для вас, поэтому итог снижен/)).toBeInTheDocument()
  expect(screen.getByRole('progressbar', { name: 'Навыки' })).toHaveAttribute('aria-valuenow', '59')
  expect(screen.getByText('Не хватает:')).toBeInTheDocument()
  expect(screen.getByText('kubernetes', { selector: 'span' })).toBeInTheDocument() // красная метка среди навыков
  expect(screen.getByText('нет данных, вес 15')).toBeInTheDocument()
  expect(screen.getByText('Подходит:')).toBeInTheDocument() // краткое объяснение сверху
  expect(screen.getByText('навыки: python, docker')).toBeInTheDocument()
  expect(screen.getByText('не хватает навыков: kubernetes')).toBeInTheDocument()
  expect(screen.getByText('зарплата в вакансии не указана', { selector: 'dd' })).toBeInTheDocument()
})

it('сообщает, что вакансия скрыта обязательными критериями', async () => {
  setup({ status: 200, body: { vacancy: detail, score: 10, hidden: true, criteria } })
  renderApp('/vacancies/5')
  expect(await screen.findByText(/В ленте скрыта/)).toBeInTheDocument()
})

it('без резюме вакансия видна, а вместо разбора ссылка на профиль', async () => {
  setup({ status: 404, body: { detail: 'Сначала загрузите резюме' } })
  renderApp('/vacancies/5')
  expect(await screen.findByRole('heading', { name: 'Python Backend' })).toBeInTheDocument()
  expect(await screen.findByText(/Сначала загрузите резюме/)).toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'Открыть профиль' })).toHaveAttribute('href', '/profile')
  expect(screen.queryByRole('progressbar')).not.toBeInTheDocument()
})
