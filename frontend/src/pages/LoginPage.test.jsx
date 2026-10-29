import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { HEALTH, USER, mockApi, renderApp } from '../test/utils.jsx'

beforeEach(() => localStorage.clear())
afterEach(() => vi.unstubAllGlobals())

function fill(email, password) {
  fireEvent.change(screen.getByLabelText('Email'), { target: { value: email } })
  fireEvent.change(screen.getByLabelText('Пароль'), { target: { value: password } })
}
const submit = (name) => fireEvent.click(screen.getByRole('button', { name }))

describe('вход и регистрация', () => {
  it('не отправляет запрос при некорректном email', async () => {
    const fetchMock = mockApi()
    renderApp('/login')
    fill('not-an-email', 'whatever123')
    submit('Войти')
    expect(await screen.findByRole('alert')).toHaveTextContent('корректный email')
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('показывает сообщение сервера при неверном пароле', async () => {
    mockApi({ 'POST /auth/login': { status: 401, body: { detail: 'Неверный email или пароль' } } })
    renderApp('/login')
    fill('ivan@example.com', 'wrong-password')
    submit('Войти')
    expect(await screen.findByRole('alert')).toHaveTextContent('Неверный email или пароль')
    expect(localStorage.getItem('jobmatch_token')).toBeNull()
  })

  it('успешный вход сохраняет токен и открывает ленту', async () => {
    mockApi({
      'POST /auth/login': { status: 200, body: { access_token: 'tok-123', token_type: 'bearer' } },
      'GET /me': { status: 200, body: USER },
      'GET /health': { status: 200, body: HEALTH },
    })
    renderApp('/login')
    fill('ivan@example.com', 'correct-horse-1')
    submit('Войти')
    expect(await screen.findByRole('heading', { name: 'Лента вакансий' })).toBeInTheDocument()
    expect(localStorage.getItem('jobmatch_token')).toBe('tok-123')
  })

  it('регистрация требует пароль от 8 символов, затем сама входит', async () => {
    const fetchMock = mockApi({
      'POST /auth/register': { status: 201, body: USER },
      'POST /auth/login': { status: 200, body: { access_token: 'tok-new', token_type: 'bearer' } },
      'GET /me': { status: 200, body: USER },
      'GET /health': { status: 200, body: HEALTH },
    })
    renderApp('/login')
    fireEvent.click(screen.getByRole('button', { name: 'Регистрация' }))
    fill('ivan@example.com', 'short')
    submit('Создать аккаунт')
    expect(await screen.findByRole('alert')).toHaveTextContent('не короче 8')
    expect(fetchMock).not.toHaveBeenCalled()

    fill('ivan@example.com', 'long-enough-pass')
    submit('Создать аккаунт')
    await waitFor(() => expect(localStorage.getItem('jobmatch_token')).toBe('tok-new'))
    const calls = fetchMock.mock.calls.map(([url, o]) => `${o?.method || 'GET'} ${url}`)
    expect(calls.slice(0, 2)).toEqual(['POST /api/auth/register', 'POST /api/auth/login'])
  })

  it('уже вошедшего со страницы входа сразу уводит в приложение', async () => {
    mockApi({ 'GET /me': { status: 200, body: USER }, 'GET /health': { status: 200, body: HEALTH } })
    localStorage.setItem('jobmatch_token', 'valid')
    renderApp('/login')
    expect(await screen.findByRole('heading', { name: 'Лента вакансий' })).toBeInTheDocument()
  })

  it('пароль можно показать и скрыть', () => {
    mockApi()
    renderApp('/login')
    const input = screen.getByLabelText('Пароль')
    expect(input).toHaveAttribute('type', 'password')
    fireEvent.click(screen.getByRole('button', { name: 'Показать пароль' }))
    expect(input).toHaveAttribute('type', 'text')
    fireEvent.click(screen.getByRole('button', { name: 'Скрыть пароль' }))
    expect(input).toHaveAttribute('type', 'password')
  })
})
