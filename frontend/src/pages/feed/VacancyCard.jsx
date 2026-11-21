import { Link } from 'react-router-dom'
import { vacancyFacts } from './labels.js'

const badge = (score) => (score >= 70 ? 'bg-green-100 text-green-800' : score >= 40 ? 'bg-amber-100 text-amber-800' : 'bg-slate-100 text-slate-600')

export default function VacancyCard({ v }) {
  const facts = vacancyFacts(v)

  return (
    <article className="h-full overflow-hidden rounded-lg border border-slate-200 bg-white p-3 text-sm">
      <div className="flex justify-between gap-3">
        <Link to={`/vacancies/${v.id}`} className="truncate font-semibold text-blue-700">
          {v.title}
        </Link>
        <div className="flex shrink-0 items-center gap-2 text-xs text-slate-400">
          {v.score != null && (
            <Link to={`/vacancies/${v.id}`} aria-label={`Оценка ${v.score}%, посмотреть разбор`} className={`rounded-full px-2 py-0.5 font-semibold ${badge(v.score)}`}>
              {v.score}%
            </Link>
          )}
          {new Date(v.published_at).toLocaleDateString('ru-RU')}
        </div>
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
