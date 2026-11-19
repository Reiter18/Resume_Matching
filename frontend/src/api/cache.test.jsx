import { act, fireEvent, render, screen, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { AuthProvider } from '../auth/AuthContext.jsx'
import { clearToken } from '../auth/token.js'
import { HEALTH, USER, mockApi, renderApp } from '../test/utils.jsx'

beforeEach(() => localStorage.setItem('jobmatch_token', 'valid'))
afterEach(() => {
  vi.unstubAllGlobals()
  localStorage.clear()
})

const routes = (patch) => ({
  'GET /me': { status: 200, body: USER },
  'GET /health': { status: 200, body: HEALTH },
  'GET /resumes/me': { status: 404, body: { detail: 'Резюме не загружено' } },
  'PATCH /me': patch,
})
const header = () => within(screen.getByRole('banner'))

async function saveName(name) {
  fireEvent.change(await screen.findByLabelText('Имя'), { target: { value: name } })
  fireEvent.click(screen.getByRole('button', { name: 'Сохранить' }))
}

it('имя в шапке меняется сразу, не дожидаясь ответа сервера', async () => {
  const original = mockApi(routes({ status: 200, body: USER })).getMockImplementation()
  vi.stubGlobal('fetch', vi.fn((url, o) => (o?.method === 'PATCH' ? new Promise(() => {}) : original(url, o)))) // ответ не придёт
  renderApp('/profile')
  await saveName('Иван')
  expect(await header().findByText('Иван')).toBeInTheDocument()
})

it('при ошибке сервера имя в шапке возвращается назад', async () => {
  mockApi(routes({ status: 500, body: { detail: 'Сбой сервера' } }))
  renderApp('/profile')
  await saveName('Иван')
  expect(await screen.findByRole('alert')).toHaveTextContent('Сбой сервера')
  expect(header().getByText('ivan@example.com')).toBeInTheDocument()
  expect(header().queryByText('Иван')).not.toBeInTheDocument()
})

it('кэш очищается при выходе, в том числе по истёкшему токену', () => {
  mockApi(routes({ status: 200, body: USER }))
  const client = new QueryClient()
  render(
    <QueryClientProvider client={client}>
      <AuthProvider>
        <span />
      </AuthProvider>
    </QueryClientProvider>,
  )
  client.setQueryData(['preferences'], { work_formats: ['remote'] })
  act(() => clearToken())
  expect(client.getQueryData(['preferences'])).toBeUndefined()
})
