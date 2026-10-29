import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError, api } from './client.js'
import { setToken } from '../auth/token.js'
import { mockApi } from '../test/utils.jsx'

beforeEach(() => localStorage.clear())
afterEach(() => vi.unstubAllGlobals())

describe('api-клиент', () => {
  it('добавляет токен в заголовок Authorization', async () => {
    const fetchMock = mockApi({ 'GET /me': { status: 200, body: { id: 1 } } })
    setToken('abc')
    await api('/me')
    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBe('Bearer abc')
  })

  it('без токена заголовка нет, а JSON-тело получает Content-Type', async () => {
    const fetchMock = mockApi({ 'POST /auth/login': { status: 200, body: {} } })
    await api('/auth/login', { method: 'POST', body: '{}' })
    const headers = fetchMock.mock.calls[0][1].headers
    expect(headers.Authorization).toBeUndefined()
    expect(headers['Content-Type']).toBe('application/json')
  })

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

  it('204 возвращает null', async () => {
    mockApi({ 'DELETE /resumes/me': { status: 204 } })
    expect(await api('/resumes/me', { method: 'DELETE' })).toBeNull()
  })
})
