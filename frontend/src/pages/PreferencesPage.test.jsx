import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { HEALTH, USER, mockApi, renderApp } from '../test/utils.jsx'

beforeEach(() => localStorage.setItem('jobmatch_token', 'valid'))
afterEach(() => {
  vi.unstubAllGlobals()
  localStorage.clear()
})

const EMPTY = {
  work_formats: [], employment_types: [], schedules: [], locations: [], min_hours_per_week: null,
  max_hours_per_week: null, min_salary: null, salary_currency: null, must_have: [],
}  // prettier-ignore

function setup(prefs) {
  let sent = null
  const fetchMock = mockApi({
    'GET /me': { status: 200, body: USER },
    'GET /health': { status: 200, body: HEALTH },
    'GET /me/preferences': { status: 200, body: prefs },
    'PUT /me/preferences': (o) => {
      sent = JSON.parse(o.body)
      return { status: 200, body: sent }
    },
  })
  renderApp('/preferences')
  return { fetchMock, sent: () => sent }
}
const group = (name) => within(screen.getByRole('group', { name }))
const mustHave = (name) => group(name).getByLabelText(/Обязательно/)

it('сохраняет выбранное и обязательные критерии', async () => {
  const { sent } = setup(EMPTY)
  await screen.findByText('Что вы ищете')
  expect(mustHave('Формат работы')).toBeDisabled() 

  fireEvent.click(group('Формат работы').getByLabelText('Удалённо'))
  fireEvent.click(mustHave('Формат работы'))
  fireEvent.change(screen.getByLabelText('Города через запятую'), { target: { value: 'Берлин, , Мюнхен' } })
  fireEvent.change(screen.getByLabelText('Не меньше, в месяц'), { target: { value: '4000' } })
  fireEvent.click(screen.getByRole('button', { name: 'Сохранить' }))

  expect(await screen.findByRole('status')).toHaveTextContent('Сохранено')
  expect(sent()).toMatchObject({
    work_formats: ['remote'], locations: ['Берлин', 'Мюнхен'], min_salary: 4000, salary_currency: 'EUR', must_have: ['work_format'],
  })
})

it('подставляет сохранённое и не отправляет обязательность для пустого критерия', async () => {
  const { sent } = setup({ ...EMPTY, work_formats: ['remote'], must_have: ['work_format'] })
  const remote = await screen.findByLabelText('Удалённо')
  expect(remote).toBeChecked()
  expect(mustHave('Формат работы')).toBeChecked()

  fireEvent.click(remote) 
  expect(mustHave('Формат работы')).toBeDisabled()
  fireEvent.click(screen.getByRole('button', { name: 'Сохранить' }))
  await waitFor(() => expect(sent()).not.toBeNull())
  expect(sent()).toMatchObject({ work_formats: [], must_have: [], min_salary: null, salary_currency: null })
})
