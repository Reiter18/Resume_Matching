import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App.jsx'

function renderAt(path) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('роутинг', () => {
  it('показывает ленту и навигацию на главной', () => {
    renderAt('/')
    expect(screen.getByRole('heading', { name: 'Лента вакансий' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Профиль и резюме' })).toBeInTheDocument()
  })

  it('открывает публичную подборку без шапки приложения', () => {
    renderAt('/s/abc123')
    expect(screen.getByRole('heading', { name: 'Публичная подборка' })).toBeInTheDocument()
    expect(screen.queryByRole('navigation')).not.toBeInTheDocument()
  })

  it('неизвестный адрес ведёт на главную', () => {
    renderAt('/нет-такой-страницы')
    expect(screen.getByRole('heading', { name: 'Лента вакансий' })).toBeInTheDocument()
  })
})
