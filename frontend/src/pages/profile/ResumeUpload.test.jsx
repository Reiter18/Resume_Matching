import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { HEALTH, USER, mockApi, renderApp } from '../../test/utils.jsx'

beforeEach(() => localStorage.setItem('jobmatch_token', 'valid'))
afterEach(() => {
  vi.unstubAllGlobals()
  localStorage.clear()
})

const RESUME = {
  id: 1, original_filename: 'cv.pdf', char_count: 321, language: 'en', preview: 'Backend developer, Python',
  skills: [], unknown_skills: [], created_at: '2026-10-20T10:00:00Z',
}
const NO_RESUME = { status: 404, body: { detail: 'Резюме не загружено' } }
const base = (extra = {}) => ({ 'GET /me': { status: 200, body: USER }, 'GET /health': { status: 200, body: HEALTH }, 'GET /resumes/me': NO_RESUME, ...extra })
const file = (name = 'cv.pdf', content = 'x'.repeat(100), type = 'application/pdf') => new File([content], name, { type })
const calls = (fetchMock, key) => {
  const [method, path] = key.split(' ')
  return fetchMock.mock.calls.filter(([url, o]) => (o?.method || 'GET') === method && url === `/api${path}`)
}
const chooseFile = (f) => fireEvent.change(document.getElementById('resume-file'), { target: { files: [f] } })

describe('загрузка файла', () => {
  it('отправляет выбранный файл как multipart и показывает загруженное резюме', async () => {
    let sent = null
    const fetchMock = mockApi(
      base({
        'POST /resumes': (o) => {
          sent = o.body
          return { status: 201, body: RESUME }
        },
      }),
    )
    renderApp('/profile')
    await screen.findByText(/Перетащите файл сюда/)
    chooseFile(file('cv.pdf'))
    expect(await screen.findByText('cv.pdf')).toBeInTheDocument()
    expect(sent).toBeInstanceOf(FormData)
    expect(sent.get('file').name).toBe('cv.pdf')
    expect(fetchMock.mock.calls.find(([u]) => u === '/api/resumes')[1].headers['Content-Type']).toBeUndefined() // браузер сам задаёт boundary
    expect(screen.getByText(/язык: английский/)).toBeInTheDocument()
  })

  it('показывает сообщение сервера, например про скан', async () => {
    mockApi(base({ 'POST /resumes': { status: 422, body: { detail: 'Не удалось извлечь текст. Если это скан, загрузите PDF с текстом' } } }))
    renderApp('/profile')
    await screen.findByText(/Перетащите файл сюда/)
    chooseFile(file('scan.pdf'))
    expect(await screen.findByRole('alert')).toHaveTextContent('скан')
    expect(screen.getByText(/Резюме пока не загружено/)).toBeInTheDocument() // состояние не испортилось
  })

  it('не отправляет запрос, если файл не подходит (формат, пустой, больше 5 МБ)', async () => {
    const fetchMock = mockApi(base())
    renderApp('/profile')
    await screen.findByText(/Перетащите файл сюда/)
    const bad = [
      [file('photo.png', 'x'.repeat(100), 'image/png'), 'PDF, DOCX и TXT'],
      [file('cv.txt', ''), 'Файл пустой'],
      [file('big.pdf', new Uint8Array(5 * 1024 * 1024 + 1)), 'больше 5 МБ'],
    ]
    for (const [f, text] of bad) {
      chooseFile(f)
      expect(await screen.findByText(text, { exact: false })).toBeInTheDocument()
    }
    expect(calls(fetchMock, 'POST /resumes')).toHaveLength(0)
  })

  it('принимает файл, перетащенный в зону', async () => {
    const fetchMock = mockApi(base({ 'POST /resumes': { status: 201, body: RESUME } }))
    renderApp('/profile')
    const zone = await screen.findByTestId('dropzone')
    fireEvent.dragOver(zone)
    fireEvent.drop(zone, { dataTransfer: { files: [file('cv.docx', 'x'.repeat(50))] } })
    expect(await screen.findByText('cv.pdf')).toBeInTheDocument()
    expect(calls(fetchMock, 'POST /resumes')).toHaveLength(1)
  })
})

describe('резюме текстом', () => {
  async function openTextTab(extra) {
    const fetchMock = mockApi(base(extra))
    renderApp('/profile')
    fireEvent.click(await screen.findByRole('button', { name: 'Вставить текстом' }))
    return fetchMock
  }

  it('слишком короткий текст не отправляется', async () => {
    const fetchMock = await openTextTab()
    fireEvent.change(screen.getByLabelText('Текст резюме'), { target: { value: 'коротко' } })
    fireEvent.click(screen.getByRole('button', { name: 'Сохранить текст' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('не короче 30')
    expect(calls(fetchMock, 'POST /resumes/text')).toHaveLength(0)
  })

  it('отправляет текст и показывает результат', async () => {
    let body = null
    await openTextTab({
      'POST /resumes/text': (o) => {
        body = JSON.parse(o.body)
        return { status: 201, body: { ...RESUME, original_filename: 'Вставленный текст' } }
      },
    })
    const text = 'Backend developer. Python FastAPI PostgreSQL Docker. Five years of experience.'
    fireEvent.change(screen.getByLabelText('Текст резюме'), { target: { value: text } })
    fireEvent.click(screen.getByRole('button', { name: 'Сохранить текст' }))
    expect(await screen.findByText('Вставленный текст')).toBeInTheDocument()
    expect(body).toEqual({ text })
  })
})

describe('замена резюме', () => {
  it('кнопка «Заменить резюме» открывает загрузку, после успеха она закрывается', async () => {
    mockApi(
      base({
        'GET /resumes/me': { status: 200, body: RESUME },
        'POST /resumes': { status: 201, body: { ...RESUME, id: 2, original_filename: 'new.pdf' } },
      }),
    )
    renderApp('/profile')
    expect(screen.queryByText(/Перетащите файл сюда/)).not.toBeInTheDocument()
    fireEvent.click(await screen.findByRole('button', { name: 'Заменить резюме' }))
    expect(screen.getByText(/заменит текущее/)).toBeInTheDocument()
    chooseFile(file('new.pdf'))
    expect(await screen.findByText('new.pdf')).toBeInTheDocument()
    await waitFor(() => expect(screen.queryByText(/Перетащите файл сюда/)).not.toBeInTheDocument())
  })
})
