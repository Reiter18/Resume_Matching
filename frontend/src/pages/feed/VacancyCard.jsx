import { Link } from 'react-router-dom'
import { EMPLOYMENT, SCHEDULES, WORK_FORMATS, formatSalary } from './labels.js'

export default function VacancyCard({ v }) {
  const facts = [
    formatSalary(v),
    WORK_FORMATS[v.work_format],
    ...v.employment_types.map((t) => EMPLOYMENT[t] || t),
    SCHEDULES[v.schedule],
    v.hours_per_week && `${v.hours_per_week} ч/нед`,
    v.experience_years_min != null && `опыт от ${v.experience_years_min} лет`,
  ].filter(Boolean)

  return (
    <article className="h-full overflow-hidden rounded-lg border border-slate-200 bg-white p-3 text-sm">
      <div className="flex justify-between gap-3">
        <Link to={`/vacancies/${v.id}`} className="truncate font-semibold text-blue-700">
          {v.title}
        </Link>
        <span className="shrink-0 text-xs text-slate-400">{new Date(v.published_at).toLocaleDateString('ru-RU')}</span>
      </div>
      <p className="truncate text-slate-600">{[v.company, v.location].filter(Boolean).join(' · ')}</p>
      <p className="mt-1 truncate text-xs text-slate-500">{facts.join(' · ') || 'Параметры не указаны'}</p>
      <ul aria-label="Навыки" className="mt-2 flex h-6 flex-wrap gap-1 overflow-hidden">
        {v.skills.slice(0, 8).map((s) => (
          <li key={s} className="rounded-full bg-blue-50 px-2 text-xs leading-6 text-blue-800">
            {s}
          </li>
        ))}
      </ul>
    </article>
  )
}
