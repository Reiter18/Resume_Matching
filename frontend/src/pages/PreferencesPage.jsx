import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client.js'
import { optimistic } from '../api/optimistic.js'
import { EMPLOYMENT, SCHEDULES, WORK_FORMATS } from './feed/labels.js'
import { buttonClass, inputClass } from './profile/Card.jsx'

const CURRENCIES = ['EUR', 'USD', 'GBP', 'RUB']
const places = (text) => text.split(',').map((s) => s.trim()).filter(Boolean)

const toForm = (p) => ({
  ...p,
  locations: p.locations.join(', '),
  min_hours_per_week: p.min_hours_per_week ?? '',
  max_hours_per_week: p.max_hours_per_week ?? '',
  min_salary: p.min_salary ?? '',
  salary_currency: p.salary_currency || 'EUR',
})

const filled = (f) => ({
  work_format: f.work_formats.length > 0,
  employment_type: f.employment_types.length > 0,
  schedule: f.schedules.length > 0,
  location: places(f.locations).length > 0,
  hours: f.min_hours_per_week !== '' || f.max_hours_per_week !== '',
  salary: Number(f.min_salary) > 0,
})

function toBody(f) {
  const ok = filled(f)
  const num = (x) => (x === '' ? null : Number(x))
  return {
    work_formats: f.work_formats,
    employment_types: f.employment_types,
    schedules: f.schedules,
    locations: places(f.locations),
    min_hours_per_week: num(f.min_hours_per_week),
    max_hours_per_week: num(f.max_hours_per_week),
    min_salary: ok.salary ? Number(f.min_salary) : null,
    salary_currency: ok.salary ? f.salary_currency : null,
    must_have: f.must_have.filter((k) => ok[k]),
  }
}

function Section({ title, name, form, set, children }) {
  const can = filled(form)[name]
  const must = form.must_have.includes(name)
  const toggle = () => set({ must_have: must ? form.must_have.filter((k) => k !== name) : [...form.must_have, name] })
  return (
    <fieldset className="rounded-lg border border-slate-200 bg-white p-4">
      <legend className="px-1 text-sm font-semibold">{title}</legend>
      {children}
      <label className="mt-3 flex items-center gap-2 text-xs text-slate-500">
        <input type="checkbox" checked={must && can} disabled={!can} onChange={toggle} />
        Обязательно: неподходящие вакансии скрываются
      </label>
    </fieldset>
  )
}

function Checks({ options, value, onChange }) {
  const toggle = (key) => onChange(value.includes(key) ? value.filter((x) => x !== key) : [...value, key])
  return (
    <div className="flex flex-wrap gap-4 text-sm">
      {Object.entries(options).map(([key, label]) => (
        <label key={key} className="flex items-center gap-2">
          <input type="checkbox" checked={value.includes(key)} onChange={() => toggle(key)} />
          {label}
        </label>
      ))}
    </div>
  )
}

function NumberField({ label, value, onChange, ...rest }) {
  return (
    <label className="flex flex-col gap-1 text-xs text-slate-500">
      {label}
      <input type="number" min="1" value={value} onChange={(e) => onChange(e.target.value)} className={inputClass} {...rest} />
    </label>
  )
}

function PreferencesForm({ initial }) {
  const queryClient = useQueryClient()
  const [form, setForm] = useState(() => toForm(initial))
  const [saved, setSaved] = useState(false)
  const set = (patch) => {
    setForm({ ...form, ...patch })
    setSaved(false)
  }
  const save = useMutation({
    mutationFn: (body) => api('/me/preferences', { method: 'PUT', body: JSON.stringify(body) }),
    ...optimistic(queryClient, ['preferences'], (_old, body) => body),
    onSuccess: (p) => {
      queryClient.setQueryData(['preferences'], p)
      setForm(toForm(p))
      setSaved(true)
    },
  })
  const section = { form, set }

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        save.mutate(toBody(form))
      }}
      className="flex flex-col gap-4"
    >
      <Section title="Формат работы" name="work_format" {...section}>
        <Checks options={WORK_FORMATS} value={form.work_formats} onChange={(v) => set({ work_formats: v })} />
      </Section>
      <Section title="Тип занятости" name="employment_type" {...section}>
        <Checks options={EMPLOYMENT} value={form.employment_types} onChange={(v) => set({ employment_types: v })} />
      </Section>
      <Section title="График" name="schedule" {...section}>
        <Checks options={SCHEDULES} value={form.schedules} onChange={(v) => set({ schedules: v })} />
      </Section>
      <Section title="Место работы" name="location" {...section}>
        <label className="flex flex-col gap-1 text-xs text-slate-500">
          Города через запятую
          <input value={form.locations} onChange={(e) => set({ locations: e.target.value })} placeholder="Берлин, Мюнхен" className={inputClass} />
        </label>
      </Section>
      <Section title="Часы в неделю" name="hours" {...section}>
        <div className="grid grid-cols-2 gap-3">
          <NumberField label="От" max="80" value={form.min_hours_per_week} onChange={(v) => set({ min_hours_per_week: v })} />
          <NumberField label="До" max="80" value={form.max_hours_per_week} onChange={(v) => set({ max_hours_per_week: v })} />
        </div>
      </Section>
      <Section title="Зарплата" name="salary" {...section}>
        <div className="grid grid-cols-[1fr_auto] gap-3">
          <NumberField label="Не меньше, в месяц" value={form.min_salary} onChange={(v) => set({ min_salary: v })} />
          <label className="flex flex-col gap-1 text-xs text-slate-500">
            Валюта
            <select value={form.salary_currency} onChange={(e) => set({ salary_currency: e.target.value })} className={inputClass}>
              {CURRENCIES.map((c) => (
                <option key={c}>{c}</option>
              ))}
            </select>
          </label>
        </div>
      </Section>
      <div className="flex items-center gap-3">
        <button type="submit" disabled={save.isPending} className={buttonClass}>
          Сохранить
        </button>
        {saved && (
          <span role="status" className="text-sm text-green-700">
            Сохранено
          </span>
        )}
        {save.isError && (
          <span role="alert" className="text-sm text-red-600">
            {save.error.message}
          </span>
        )}
      </div>
    </form>
  )
}

export default function PreferencesPage() {
  const { data, isPending, isError, error } = useQuery({ queryKey: ['preferences'], queryFn: () => api('/me/preferences') })
  return (
    <div className="max-w-2xl">
      <h1 className="mb-1 text-xl font-semibold">Что вы ищете</h1>
      <p className="mb-4 text-sm text-slate-500">Пустые поля в оценке вакансий не учитываются: заполните то, что для вас важно.</p>
      {isPending && <p className="text-sm text-slate-500">Загрузка…</p>}
      {isError && (
        <p role="alert" className="text-sm text-red-600">
          {error.message}
        </p>
      )}
      {data && <PreferencesForm initial={data} />}
    </div>
  )
}
