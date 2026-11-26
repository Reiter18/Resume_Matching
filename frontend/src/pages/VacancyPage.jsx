import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client.js'
import { vacancyFacts } from './feed/labels.js'
import MatchBreakdown from './vacancy/MatchBreakdown.jsx'

export default function VacancyPage() {
  const { id } = useParams()
  const vacancy = useQuery({ queryKey: ['vacancy', id], queryFn: () => api(`/vacancies/${id}`) })
  const match = useQuery({ queryKey: ['match', id], queryFn: () => api(`/matches/${id}`), retry: false }) 

  const v = vacancy.data
  return (
    <div>
      <Link to="/" className="mb-4 inline-block text-sm text-blue-600 underline">
        ← К ленте
      </Link>
      {vacancy.isPending && <p className="text-sm text-slate-500">Загрузка…</p>}
      {vacancy.isError && (
        <p role="alert" className="text-sm text-red-600">
          {vacancy.error.message}
        </p>
      )}
      {v && (
        <div className="grid gap-6 lg:grid-cols-[1fr_22rem]">
          <article>
            <h1 className="text-xl font-semibold">{v.title}</h1>
            <p className="text-slate-600">{[v.company, v.location].filter(Boolean).join(' · ')}</p>
            <p className="mt-1 text-sm text-slate-500">{vacancyFacts(v).join(' · ') || 'Параметры не указаны'}</p>
            <p className="mt-3 flex flex-wrap gap-3 text-sm">
              <a href={v.url} target="_blank" rel="noopener noreferrer" className="font-medium text-blue-700 underline">
                Открыть на {v.source}
              </a>
              {v.also_found_at.length > 0 && (
                <span className="text-slate-500">
                  Также найдено:{' '}
                  {v.also_found_at.map((o) => (
                    <a key={o.url} href={o.url} target="_blank" rel="noopener noreferrer" className="mr-2 underline">
                      {o.source}
                    </a>
                  ))}
                </span>
              )}
            </p>
            <ul aria-label="Навыки" className="mt-3 flex flex-wrap gap-1">
              {v.skills.map((s) => (
                <li key={s} className="rounded-full bg-blue-50 px-2 py-0.5 text-xs text-blue-800">
                  {s}
                </li>
              ))}
            </ul>
            <p className="mt-4 whitespace-pre-line text-sm text-slate-800">{v.description_text}</p>
          </article>
          <aside>
            {match.isSuccess && (
              <>
                {match.data.hidden && <p className="mb-3 rounded-md bg-amber-50 p-3 text-xs text-amber-800">В ленте скрыта: не подходит под ваши обязательные критерии.</p>}
                <MatchBreakdown score={match.data.score} confidence={match.data.confidence} summary={match.data.summary} criteria={match.data.criteria} />
              </>
            )}
            {match.isError && (
              <p className="rounded-md bg-slate-50 p-3 text-sm text-slate-600">
                {match.error.message}.{' '}
                <Link to="/profile" className="underline">
                  Открыть профиль
                </Link>
              </p>
            )}
          </aside>
        </div>
      )}
    </div>
  )
}
