import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { HEALTH, USER, mockApi, renderApp } from '../test/utils.jsx'

beforeEach(() => localStorage.setItem('jobmatch_token', 'valid'))
afterEach(() => {
  vi.unstubAllGlobals()
  localStorage.clear()
})

const NO_RESUME = { status: 404, body: { detail: 'Резюме не загружено' } }
const RESUME = { id: 1, original_filename: 'cv.pdf', char_count: 321, language: 'ru', preview: 'Backend developer, Python', skills: [], created_at: '2026-10-20T10:00:00Z' }
const base = (extra = {}) => ({ 'GET /me': { status: 200, body: USER }, 'GET /health': { status: 200, body: HEALTH }, 'GET /resumes/me': NO_RESUME, ...extra })
const callsTo = (fetchMock, key) => fetchMock.mock.calls.filter(([url, o]) => `${o?.method || 'GET'} ${url}` === `${key.split(' ')[0]} /api${key.split(' ')[1]}`)
const typeInto = (label, value) => fireEvent.change(screen.getByLabelText(label), { target: { value } })

describe('аккаунт', () => {
  it('показывает email и дату регистрации', async () => {
    mockApi(base())
    renderApp('/profile')
    expect(await screen.findByRole('heading', { name: 'Профиль и резюме' })).toBeInTheDocument()
    expect((await screen.findAllByText(USER.email)).length).toBeGreaterThan(0)
    expect(screen.getByText('05.10.2026')).toBeInTheDocument()
  })

  it('сохраняет имя и показывает его в шапке', async () => {
    let name = null
    const fetchMock = mockApi(
      base({
        'PATCH /me': (o) => {
          name = JSON.parse(o.body).full_name
          return { status: 200, body: { ...USER, full_name: name } }
        },
      }),
    )
    renderApp('/profile')
    await screen.findByLabelText('Имя')
    typeInto('Имя', 'Иван Петров')
    fireEvent.click(screen.getByRole('button', { name: 'Сохранить' }))
    expect(await screen.findByRole('status')).toHaveTextContent('Сохранено')
    expect(name).toBe('Иван Петров')
    expect(callsTo(fetchMock, 'PATCH /me')).toHaveLength(1)
  })
})

describe('смена пароля', () => {
  async function open(extra) {
    const fetchMock = mockApi(base(extra))
    renderApp('/profile')
    await screen.findByLabelText('Текущий пароль')
    return fetchMock
  }
  const fillAll = (cur, next, rep) => {
    typeInto('Текущий пароль', cur)
    typeInto('Новый пароль', next)
    typeInto('Повторите новый пароль', rep)
    fireEvent.click(screen.getByRole('button', { name: 'Сменить пароль' }))
  }

  it.each([
    ['old-password-1', 'short', 'short', 'не короче 8'],
    ['old-password-1', 'new-password-22', 'different-pass-3', 'не совпадают'],
    ['old-password-1', 'old-password-1', 'old-password-1', 'совпадает с текущим'],
    ['', 'new-password-22', 'new-password-22', 'текущий пароль'],
  ])('не отправляет запрос при ошибке в форме (%#)', async (cur, next, rep, text) => {
    const fetchMock = await open()
    fillAll(cur, next, rep)
    expect(await screen.findByRole('alert')).toHaveTextContent(text)
    expect(callsTo(fetchMock, 'POST /me/password')).toHaveLength(0)
  })

  it('меняет пароль, очищает поля и пишет подтверждение', async () => {
    let body = null
    await open({
      'POST /me/password': (o) => {
        body = JSON.parse(o.body)
        return { status: 204 }
      },
    })
    fillAll('old-password-1', 'new-password-22', 'new-password-22')
    expect(await screen.findByText('Пароль изменён')).toBeInTheDocument()
    expect(body).toEqual({ current_password: 'old-password-1', new_password: 'new-password-22' })
    expect(screen.getByLabelText('Текущий пароль')).toHaveValue('')
  })

  it('показывает ошибку сервера и не разлогинивает', async () => {
    await open({ 'POST /me/password': { status: 400, body: { detail: 'Неверный текущий пароль' } } })
    fillAll('wrong-password', 'new-password-22', 'new-password-22')
    expect(await screen.findByRole('alert')).toHaveTextContent('Неверный текущий пароль')
    expect(localStorage.getItem('jobmatch_token')).toBe('valid')
  })
})

describe('резюме', () => {
  it('сообщает, что резюме нет', async () => {
    mockApi(base())
    renderApp('/profile')
    expect(await screen.findByText(/Резюме пока не загружено/)).toBeInTheDocument()
  })

  it('показывает файл, язык и по кнопке полный текст', async () => {
    mockApi(base({ 'GET /resumes/me': { status: 200, body: RESUME }, 'GET /resumes/me/text': { status: 200, body: { text: 'ПОЛНЫЙ ТЕКСТ РЕЗЮМЕ' } } }))
    renderApp('/profile')
    expect(await screen.findByText('cv.pdf')).toBeInTheDocument()
    expect(screen.getByText(/321 символов · язык: русский/)).toBeInTheDocument()
    expect(screen.getByText('Backend developer, Python')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Показать полный текст' }))
    expect(await screen.findByText('ПОЛНЫЙ ТЕКСТ РЕЗЮМЕ')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Свернуть' }))
    expect(await screen.findByText('Backend developer, Python')).toBeInTheDocument()
  })

  it('удаление резюме требует подтверждения', async () => {
    let deleted = false
    const fetchMock = mockApi(
      base({
        'GET /resumes/me': () => (deleted ? NO_RESUME : { status: 200, body: RESUME }),
        'DELETE /resumes/me': () => {
          deleted = true
          return { status: 204 }
        },
      }),
    )
    renderApp('/profile')
    fireEvent.click(await screen.findByRole('button', { name: 'Удалить резюме' }))
    expect(callsTo(fetchMock, 'DELETE /resumes/me')).toHaveLength(0) // пока только спросили
    fireEvent.click(screen.getByRole('button', { name: 'Да, удалить' }))
    expect(await screen.findByText(/Резюме пока не загружено/)).toBeInTheDocument()
    expect(callsTo(fetchMock, 'DELETE /resumes/me')).toHaveLength(1)
  })
})

describe('удаление аккаунта и выход', () => {
  it('неверный пароль: ошибка, пользователь остаётся в системе', async () => {
    mockApi(base({ 'DELETE /me': { status: 400, body: { detail: 'Неверный пароль' } } }))
    renderApp('/profile')
    fireEvent.click(await screen.findByRole('button', { name: 'Удалить аккаунт' }))
    expect(screen.getByRole('button', { name: 'Удалить навсегда' })).toBeDisabled() // без пароля нельзя
    typeInto('Пароль для подтверждения', 'wrong-pass-1')
    fireEvent.click(screen.getByRole('button', { name: 'Удалить навсегда' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Неверный пароль')
    expect(localStorage.getItem('jobmatch_token')).toBe('valid')
  })

  it('верный пароль: аккаунт удалён, выход на страницу входа', async () => {
    let body = null
    mockApi(
      base({
        'DELETE /me': (o) => {
          body = JSON.parse(o.body)
          return { status: 204 }
        },
      }),
    )
    renderApp('/profile')
    fireEvent.click(await screen.findByRole('button', { name: 'Удалить аккаунт' }))
    typeInto('Пароль для подтверждения', 'correct-horse-1')
    fireEvent.click(screen.getByRole('button', { name: 'Удалить навсегда' }))
    expect(await screen.findByRole('button', { name: 'Войти' })).toBeInTheDocument()
    expect(body).toEqual({ password: 'correct-horse-1' })
    expect(localStorage.getItem('jobmatch_token')).toBeNull()
  })

  it('можно передумать: «Отмена» возвращает кнопку', async () => {
    mockApi(base())
    renderApp('/profile')
    fireEvent.click(await screen.findByRole('button', { name: 'Удалить аккаунт' }))
    fireEvent.click(screen.getByRole('button', { name: 'Отмена' }))
    expect(screen.getByRole('button', { name: 'Удалить аккаунт' })).toBeInTheDocument()
  })

  it('кнопка «Выйти» очищает токен и ведёт на вход', async () => {
    mockApi(base())
    renderApp('/profile')
    const header = (await screen.findByRole('navigation')).closest('header')
    fireEvent.click(within(header).getByRole('button', { name: 'Выйти' }))
    expect(await screen.findByRole('button', { name: 'Войти' })).toBeInTheDocument()
    expect(localStorage.getItem('jobmatch_token')).toBeNull()
  })
})

describe('шапка', () => {
  it('показывает имя вместо email, если оно задано', async () => {
    mockApi(base({ 'GET /me': { status: 200, body: { ...USER, full_name: 'Иван Петров' } } }))
    renderApp('/profile')
    await waitFor(() => expect(within(document.querySelector('header')).getByText('Иван Петров')).toBeInTheDocument())
  })
})
