import { cleanup, fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { HEALTH, USER, mockApi, renderApp } from '../test/utils.jsx'

beforeEach(() => localStorage.setItem('jobmatch_token', 'valid'))
afterEach(() => {
  vi.unstubAllGlobals()
  localStorage.clear()
})

const vacancy = (id) => ({
  id, title: `Вакансия ${id}`, company: 'Acme', location: 'Berlin', work_format: 'remote', employment_types: ['full_time'],
  schedule: null, hours_per_week: null, experience_years_min: 3, salary_min: 4000, salary_max: 5000, salary_currency: 'EUR',
  tags: [], skills: ['python', 'docker'], published_at: '2026-11-01T10:00:00Z', url: 'https://x', source: 'arbeitnow',
})
const page = (offset, count, total) => ({
  status: 200,
  body: { items: Array.from({ length: count }, (_, i) => vacancy(offset + i + 1)), total, limit: 20, offset },
})
const base = (extra) => ({ 'GET /me': { status: 200, body: USER }, 'GET /health': { status: 200, body: HEALTH }, ...extra })
const urls = (fetchMock) => fetchMock.mock.calls.map(([url]) => url).filter((u) => u.startsWith('/api/vacancies'))

it('рисует только видимые строки и подгружает следующую страницу при прокрутке', async () => {
  const fetchMock = mockApi(base({ 'GET /vacancies?limit=20&offset=0': page(0, 20, 45), 'GET /vacancies?limit=20&offset=20': page(20, 20, 45) }))
  renderApp('/')
  expect(await screen.findByText('Вакансия 1')).toBeInTheDocument()
  expect(screen.getByText('Найдено: 45')).toBeInTheDocument()
  expect(screen.getAllByRole('article').length).toBeLessThan(20) 
  expect(screen.queryByText('Вакансия 15')).not.toBeInTheDocument()

  const list = screen.getByRole('region', { name: 'Список вакансий' })
  list.scrollTop = 1800
  fireEvent.scroll(list)
  expect(await screen.findByText('Вакансия 15')).toBeInTheDocument()
  await waitFor(() => expect(urls(fetchMock)).toContain('/api/vacancies?limit=20&offset=20'))
})

it('фильтр уходит на сервер после паузы в наборе, а не на каждую букву', async () => {
  const fetchMock = mockApi(base({ 'GET /vacancies?limit=20&offset=0': page(0, 2, 2), 'GET /vacancies?limit=20&offset=0&q=python': page(0, 1, 1) }))
  renderApp('/')
  await screen.findByText('Вакансия 2')
  fireEvent.change(screen.getByLabelText('Поиск'), { target: { value: 'pyth' } })
  fireEvent.change(screen.getByLabelText('Поиск'), { target: { value: 'python' } })
  expect(urls(fetchMock)).toHaveLength(1)
  await waitFor(() => expect(screen.queryByText('Вакансия 2')).not.toBeInTheDocument())
  await waitFor(() => expect(urls(fetchMock)).toEqual(['/api/vacancies?limit=20&offset=0', '/api/vacancies?limit=20&offset=0&q=python']))
})

it('показывает пустой результат и ошибку сервера', async () => {
  mockApi(base({ 'GET /vacancies?limit=20&offset=0': page(0, 0, 0) }))
  renderApp('/')
  expect(await screen.findByText(/Ничего не найдено/)).toBeInTheDocument()

  cleanup()
  mockApi(base({ 'GET /vacancies?limit=20&offset=0': { status: 500, body: { detail: 'Сбой сервера' } } }))
  renderApp('/')
  expect(await screen.findByRole('alert')).toHaveTextContent('Сбой сервера')
})
