import { screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { HEALTH, USER, mockApi, renderApp } from './test/utils.jsx'
import { setToken } from './auth/token.js'

beforeEach(() => localStorage.clear())
afterEach(() => vi.unstubAllGlobals())

describe('роутинг и защита страниц', () => {
  it('гостя с главной отправляет на страницу входа', async () => {
    mockApi()
    renderApp('/')
    expect(await screen.findByRole('button', { name: 'Войти' })).toBeInTheDocument()
    expect(screen.queryByRole('navigation')).not.toBeInTheDocument()
  })

  it('вошедший видит ленту, навигацию и свой email', async () => {
    mockApi({ 'GET /me': { status: 200, body: USER }, 'GET /health': { status: 200, body: HEALTH } })
    setToken('valid-token')
    renderApp('/')
    expect(await screen.findByRole('heading', { name: 'Лента вакансий' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Профиль и резюме' })).toBeInTheDocument()
    expect(screen.getByText(USER.email)).toBeInTheDocument()
  })

  it('публичная подборка открывается без входа и без шапки приложения', () => {
    mockApi()
    renderApp('/s/abc123')
    expect(screen.getByRole('heading', { name: 'Публичная подборка' })).toBeInTheDocument()
    expect(screen.queryByRole('navigation')).not.toBeInTheDocument()
  })

  it('неизвестный адрес ведёт на главную, а гостя дальше на вход', async () => {
    mockApi()
    renderApp('/нет-такой-страницы')
    expect(await screen.findByRole('button', { name: 'Войти' })).toBeInTheDocument()
  })

  it('просроченный токен (401 на /me) выбрасывает на вход', async () => {
    mockApi({ 'GET /me': { status: 401, body: { detail: 'Требуется вход' } } })
    setToken('expired-token')
    renderApp('/profile')
    expect(await screen.findByRole('button', { name: 'Войти' })).toBeInTheDocument()
    expect(localStorage.getItem('jobmatch_token')).toBeNull()
  })
})
