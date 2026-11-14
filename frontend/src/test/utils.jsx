import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { vi } from 'vitest'
import App from '../App.jsx'
import { AuthProvider } from '../auth/AuthContext.jsx'

export function mockApi(routes = {}) {
  const fn = vi.fn(async (url, options = {}) => {
    const key = `${(options.method || 'GET').toUpperCase()} ${String(url).replace(/^\/api/, '')}`
    const hit = routes[key] || { status: 404, body: { detail: 'Не найдено' } }
    const res = typeof hit === 'function' ? hit(options) : hit
    return new Response(res.status === 204 ? null : JSON.stringify(res.body ?? {}), {
      status: res.status,
      headers: { 'Content-Type': 'application/json' },
    })
  })
  vi.stubGlobal('fetch', fn)
  return fn
}

export const USER = { id: 1, email: 'ivan@example.com', created_at: '2026-10-05T10:00:00Z' }
export const HEALTH = { status: 'ok', db: true, redis: true }

export function renderApp(path = '/') {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <AuthProvider>
          <App />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}
