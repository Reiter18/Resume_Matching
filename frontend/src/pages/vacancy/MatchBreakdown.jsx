import { CRITERIA } from '../feed/labels.js'

const STATUS = {
  match: { label: 'совпало', bar: 'bg-green-500', text: 'text-green-700' },
  partial: { label: 'частично', bar: 'bg-amber-500', text: 'text-amber-700' },
  mismatch: { label: 'не подходит', bar: 'bg-red-500', text: 'text-red-700' },
  unknown: { label: 'нет данных', bar: 'bg-slate-300', text: 'text-slate-500' },
}

function Chips({ title, items, className }) {
  if (!items?.length) return null
  return (
    <p className="mt-1 flex flex-wrap items-center gap-1 text-xs">
      <span className="text-slate-500">{title}:</span>
      {items.map((s) => (
        <span key={s} className={`rounded-full px-2 py-0.5 ${className}`}>
          {s}
        </span>
      ))}
    </p>
  )
}

export default function MatchBreakdown({ score, criteria }) {
  const rows = Object.entries(criteria).sort((a, b) => b[1].weight - a[1].weight)
  const known = rows.filter(([, c]) => c.score !== null).length
  return (
    <section aria-label="Разбор оценки" className="rounded-lg border border-slate-200 bg-white p-4">
      <h2 className="text-lg font-semibold">{score == null ? 'Оценка недоступна' : `Почему ${score}%`}</h2>
      <p className="mb-4 text-xs text-slate-500">
        Посчитано по {known} из {rows.length} критериев. Чем больше вес, тем важнее критерий.
      </p>
      <ul className="flex flex-col gap-4">
        {rows.map(([key, c]) => {
          const st = STATUS[c.status]
          return (
            <li key={key}>
              <div className="flex justify-between text-sm">
                <span className="font-medium">{CRITERIA[key] || key}</span>
                <span className={st.text}>
                  {st.label}, вес {c.weight}
                </span>
              </div>
              <div role="progressbar" aria-label={CRITERIA[key] || key} aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round((c.score ?? 0) * 100)} className="mt-1 h-2 rounded bg-slate-100">
                <div className={`h-2 rounded ${st.bar}`} style={{ width: `${(c.score ?? 0) * 100}%` }} />
              </div>
              <p className="mt-1 text-xs text-slate-600">{c.text}</p>
              <Chips title="Есть" items={c.matched} className="bg-green-50 text-green-800" />
              <Chips title="Не хватает" items={c.missing} className="bg-red-50 text-red-800" />
            </li>
          )
        })}
      </ul>
    </section>
  )
}
