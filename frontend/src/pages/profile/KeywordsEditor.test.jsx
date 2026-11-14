import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { HEALTH, USER, mockApi, renderApp } from '../../test/utils.jsx'

beforeEach(() => localStorage.setItem('jobmatch_token', 'valid'))
afterEach(() => {
  vi.unstubAllGlobals()
  localStorage.clear()
})

const resume = (skills = [], unknown_skills = []) => ({
  id: 1, original_filename: 'cv.pdf', char_count: 321, language: 'en', preview: 'Backend developer',
  skills, unknown_skills, created_at: '2026-10-20T10:00:00Z',
})
const base = (r, extra = {}) => ({
  'GET /me': { status: 200, body: USER },
  'GET /health': { status: 200, body: HEALTH },
  'GET /resumes/me': { status: 200, body: r },
  ...extra,
})
const calls = (fetchMock, key) => {
  const [method, path] = key.split(' ')
  return fetchMock.mock.calls.filter(([url, o]) => (o?.method || 'GET') === method && url === `/api${path}`)
}
const chips = () => within(screen.getByRole('list', { name: 'Ключевые слова резюме' })).getAllByRole('listitem').map((li) => li.textContent.replace('×', ''))
const input = () => screen.getByLabelText('Добавить ключевое слово')
const type = (value) => fireEvent.change(input(), { target: { value } })
const normalizeRoute = (map) => (o) => {
  const names = JSON.parse(o.body).names
  const skills = [...new Set(names.map((n) => map[n.toLowerCase()] || n.toLowerCase()))]
  return { status: 200, body: { skills, unknown: skills.filter((s) => !Object.values(map).includes(s)) } }
}

describe('ключевые слова', () => {
  it('показывает слова резюме и помечает слова не из словаря', async () => {
    mockApi(base(resume(['python', 'кулинария'], ['кулинария'])))
    renderApp('/profile')
    await screen.findByLabelText('Добавить ключевое слово')
    expect(chips()).toEqual(['python', 'кулинария'])
    expect(screen.getByText('кулинария', { exact: false }).closest('li')).toHaveAttribute('title', expect.stringContaining('Нет в словаре'))
    expect(screen.getByText('python', { exact: false }).closest('li')).not.toHaveAttribute('title')
  })

  it('Enter добавляет слово после нормализации, повторы игнорируются', async () => {
    const fetchMock = mockApi(base(resume(['postgresql']), { 'POST /skills/normalize': normalizeRoute({ postgres: 'postgresql', js: 'javascript' }) }))
    renderApp('/profile')
    await screen.findByLabelText('Добавить ключевое слово')
    type('JS')
    fireEvent.keyDown(input(), { key: 'Enter' })
    await waitFor(() => expect(chips()).toEqual(['postgresql', 'javascript']))
    expect(input()).toHaveValue('')
    type('Postgres') // синоним уже добавленного слова
    fireEvent.keyDown(input(), { key: 'Enter' })
    await waitFor(() => expect(calls(fetchMock, 'POST /skills/normalize')).toHaveLength(2))
    expect(chips()).toEqual(['postgresql', 'javascript'])
  })

  it('слова через запятую добавляются одним запросом', async () => {
    const fetchMock = mockApi(base(resume(), { 'POST /skills/normalize': normalizeRoute({ docker: 'docker', питон: 'python' }) }))
    renderApp('/profile')
    await screen.findByLabelText('Добавить ключевое слово')
    type('питон, docker , кулинария')
    fireEvent.keyDown(input(), { key: 'Enter' })
    await waitFor(() => expect(chips()).toEqual(['python', 'docker', 'кулинария']))
    expect(calls(fetchMock, 'POST /skills/normalize')).toHaveLength(1)
    expect(JSON.parse(calls(fetchMock, 'POST /skills/normalize')[0][1].body).names).toEqual(['питон', 'docker', 'кулинария'])
    expect(screen.getByText('кулинария', { exact: false }).closest('li')).toHaveAttribute('title') // слово не из словаря помечено сразу
  })

  it('подсказки: после паузы показываются варианты, клик добавляет слово без нормализации', async () => {
    const fetchMock = mockApi(
      base(resume(), {
        'GET /skills?q=py&limit=8': {
          status: 200,
          body: [
            { name: 'python', category: 'language', weight: 1, matched_alias: null },
            { name: 'pytest', category: 'tool', weight: 1, matched_alias: null },
          ],
        },
      }),
    )
    renderApp('/profile')
    await screen.findByLabelText('Добавить ключевое слово')
    fireEvent.focus(input())
    type('py')
    expect(calls(fetchMock, 'GET /skills?q=py&limit=8')).toHaveLength(0) // сразу запроса нет, ждём паузу
    const option = await screen.findByRole('option', { name: /python/ })
    expect(calls(fetchMock, 'GET /skills?q=py&limit=8')).toHaveLength(1)
    fireEvent.mouseDown(option)
    await waitFor(() => expect(chips()).toEqual(['python']))
    expect(calls(fetchMock, 'POST /skills/normalize')).toHaveLength(0)
  })

  it('удаление слова крестиком и Backspace, отмена изменений', async () => {
    mockApi(base(resume(['python', 'docker', 'git'])))
    renderApp('/profile')
    await screen.findByLabelText('Добавить ключевое слово')
    fireEvent.click(screen.getByRole('button', { name: 'Удалить docker' }))
    expect(chips()).toEqual(['python', 'git'])
    fireEvent.keyDown(input(), { key: 'Backspace' })
    expect(chips()).toEqual(['python'])
    expect(screen.getByText('Есть несохранённые изменения')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Отменить изменения' }))
    expect(chips()).toEqual(['python', 'docker', 'git'])
    expect(screen.queryByText('Есть несохранённые изменения')).not.toBeInTheDocument()
  })

  it('сохраняет слова и показывает ответ сервера', async () => {
    let body = null
    mockApi(
      base(resume(['python', 'docker']), {
        'PUT /resumes/me/skills': (o) => {
          body = JSON.parse(o.body)
          return { status: 200, body: resume(['python'], []) }
        },
      }),
    )
    renderApp('/profile')
    await screen.findByLabelText('Добавить ключевое слово')
    fireEvent.click(screen.getByRole('button', { name: 'Удалить docker' }))
    fireEvent.click(screen.getByRole('button', { name: 'Сохранить слова' }))
    expect(await screen.findByRole('status')).toHaveTextContent('Сохранено')
    expect(body).toEqual({ skills: ['python'] })
    expect(chips()).toEqual(['python'])
    expect(screen.getByRole('button', { name: 'Сохранить слова' })).toBeDisabled()
  })

  it('ошибки нормализации и сохранения не ломают редактор', async () => {
    mockApi(
      base(resume(['python']), {
        'POST /skills/normalize': { status: 422, body: { detail: 'Проверьте введённые данные' } },
        'PUT /resumes/me/skills': { status: 500, body: { detail: 'Ошибка сервера' } },
      }),
    )
    renderApp('/profile')
    await screen.findByLabelText('Добавить ключевое слово')
    type('docker')
    fireEvent.keyDown(input(), { key: 'Enter' })
    expect(await screen.findByRole('alert')).toHaveTextContent('Проверьте введённые данные')
    expect(chips()).toEqual(['python'])
    fireEvent.click(screen.getByRole('button', { name: 'Удалить python' }))
    fireEvent.click(screen.getByRole('button', { name: 'Сохранить слова' }))
    await waitFor(() => expect(screen.getAllByRole('alert').some((a) => a.textContent.includes('Ошибка сервера'))).toBe(true))
  })

})
