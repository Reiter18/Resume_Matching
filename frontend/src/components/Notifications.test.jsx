import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { HEALTH, USER, mockApi, renderApp } from '../test/utils.jsx'

beforeEach(() => localStorage.setItem('jobmatch_token', 'valid'))
afterEach(() => {
  vi.unstubAllGlobals()
  localStorage.clear()
})

const empty = { status: 200, body: { items: [], total: 0, limit: 20, offset: 0, pending: false } }

it('новое событие обновляет ленту и показывает уведомление, даже если пришло по частям', async () => {
  const chunks = ['data: {"type":"new_matches","count":2,', '"best":{"id":7,"title":"Python Backend","score":91}}\n\n']
  let streamController
  const stream = new ReadableStream({
    start(controller) {
      streamController = controller
    },
  })
  const api = mockApi({
    'GET /me': { status: 200, body: USER },
    'GET /health': { status: 200, body: HEALTH },
    'GET /matches?limit=20&offset=0': empty,
  }).getMockImplementation()
  const fetchMock = vi.fn((url, options) => (url === '/api/events' ? Promise.resolve(new Response(stream, { status: 200 })) : api(url, options)))
  vi.stubGlobal('fetch', fetchMock)
  const feedRequests = () => fetchMock.mock.calls.filter(([url]) => url.startsWith('/api/matches')).length

  renderApp('/')
  await screen.findByText(/Подходящих вакансий пока нет/)
  for (const chunk of chunks) streamController.enqueue(new TextEncoder().encode(chunk))

  expect(await screen.findByText('Новых подходящих вакансий: 2')).toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'Python Backend' })).toHaveAttribute('href', '/vacancies/7')
  expect(screen.getByText('Лучшая оценка: 91%')).toBeInTheDocument()
  expect(fetchMock.mock.calls.find(([url]) => url === '/api/events')[1].headers.Authorization).toBe('Bearer valid')
  await waitFor(() => expect(feedRequests()).toBeGreaterThanOrEqual(2))

  fireEvent.click(screen.getByRole('button', { name: 'Закрыть' }))
  expect(screen.queryByText(/Новых подходящих/)).not.toBeInTheDocument()
})
