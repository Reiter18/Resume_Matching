import { inputClass } from '../profile/Card.jsx'
import { EMPLOYMENT, WORK_FORMATS } from './labels.js'

export const EMPTY = { q: '', work_format: '', employment_type: '', min_salary: '', skill: '' }

function Field({ label, children }) {
  return (
    <label className="flex flex-col gap-1 text-xs text-slate-500">
      {label}
      {children}
    </label>
  )
}

function Select({ value, onChange, options, any }) {
  return (
    <select value={value} onChange={onChange} className={inputClass}>
      <option value="">{any}</option>
      {Object.entries(options).map(([key, label]) => (
        <option key={key} value={key}>
          {label}
        </option>
      ))}
    </select>
  )
}

export default function Filters({ value, onChange }) {
  const set = (key) => (e) => onChange({ ...value, [key]: e.target.value })
  return (
    <div className="mb-4 grid gap-3 rounded-lg border border-slate-200 bg-white p-4 sm:grid-cols-2 lg:grid-cols-5">
      <Field label="Поиск">
        <input value={value.q} onChange={set('q')} placeholder="название или компания" maxLength={100} className={inputClass} />
      </Field>
      <Field label="Формат работы">
        <Select value={value.work_format} onChange={set('work_format')} options={WORK_FORMATS} any="Любой" />
      </Field>
      <Field label="Занятость">
        <Select value={value.employment_type} onChange={set('employment_type')} options={EMPLOYMENT} any="Любая" />
      </Field>
      <Field label="Зарплата от, в месяц">
        <input type="number" min="0" value={value.min_salary} onChange={set('min_salary')} placeholder="только с зарплатой" className={inputClass} />
      </Field>
      <Field label="Навык">
        <input value={value.skill} onChange={set('skill')} placeholder="python, питон, k8s" maxLength={50} className={inputClass} />
      </Field>
      {Object.values(value).some(Boolean) && (
        <button type="button" onClick={() => onChange(EMPTY)} className="text-left text-sm text-blue-600 underline sm:col-span-2 lg:col-span-5">
          Сбросить фильтры
        </button>
      )}
    </div>
  )
}
