import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError, api } from './client.js'
import { setToken } from '../auth/token.js'
import { mockApi } from '../test/utils.jsx'

beforeEach(() => localStorage.clear())
afterEach(() => vi.unstubAllGlobals())

describe('api-клиент', () => {
  it('берёт текст ошибки из ответа сервера', async () => {
    mockApi({ 'GET /x': { status: 409, body: { detail: 'Уже есть' } } })
    await expect(api('/x')).rejects.toMatchObject({ status: 409, message: 'Уже есть' })
    mockApi({ 'GET /y': { status: 422, body: { detail: [{ msg: 'bad' }] } } })
    await expect(api('/y')).rejects.toThrow('Проверьте введённые данные')
    await expect(api('/y')).rejects.toBeInstanceOf(ApiError)
  })

  it('401 при действующем токене очищает его, 401 на входе токен не трогает', async () => {
    mockApi({ 'GET /me': { status: 401, body: { detail: 'Требуется вход' } } })
    setToken('old')
    await expect(api('/me')).rejects.toBeDefined()
    expect(localStorage.getItem('jobmatch_token')).toBeNull()

    mockApi({ 'POST /auth/login': { status: 401, body: { detail: 'Неверный email или пароль' } } })
    setToken('keep')
    await expect(api('/auth/login', { method: 'POST', body: '{}' })).rejects.toBeDefined()
    expect(localStorage.getItem('jobmatch_token')).toBe('keep')
  })

})

describe('api-клиент: заголовки и ответы', () => {
  it('токен идёт в Authorization, JSON-тело получает Content-Type, 204 даёт null', async () => {
    const fetchMock = mockApi({ 'GET /me': { status: 200, body: { id: 1 } }, 'POST /auth/login': { status: 200, body: {} }, 'DELETE /resumes/me': { status: 204 } })
    await api('/auth/login', { method: 'POST', body: '{}' })
    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBeUndefined() 
    expect(fetchMock.mock.calls[0][1].headers['Content-Type']).toBe('application/json')
    setToken('abc')
    await api('/me')
    expect(fetchMock.mock.calls[1][1].headers.Authorization).toBe('Bearer abc')
    expect(await api('/resumes/me', { method: 'DELETE' })).toBeNull()
  })
})
