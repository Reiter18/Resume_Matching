import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useDebouncedValue } from '../hooks/useDebouncedValue.js'
import FeedList from './feed/FeedList.jsx'
import Filters, { EMPTY } from './feed/Filters.jsx'
import { inputClass } from './profile/Card.jsx'

const MIN_SCORES = [['', 'Любая оценка'], ['50', 'от 50%'], ['70', 'от 70%'], ['85', 'от 85%']]

function AllVacancies() {
  const [filters, setFilters] = useState(EMPTY)
  const applied = JSON.parse(useDebouncedValue(JSON.stringify(filters), 300)) 
  return (
    <>
      <Filters value={filters} onChange={setFilters} />
      <FeedList path="/vacancies" filters={applied} emptyText="Ничего не найдено. Измените фильтры." />
    </>
  )
}

function BestMatches() {
  const [minScore, setMinScore] = useState('')
  return (
    <>
      <label className="mb-4 flex w-48 flex-col gap-1 text-xs text-slate-500">
        Оценка
        <select value={minScore} onChange={(e) => setMinScore(e.target.value)} className={inputClass}>
          {MIN_SCORES.map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </label>
      <FeedList path="/matches" filters={{ min_score: minScore }} emptyText="Подходящих вакансий пока нет. Попробуйте смягчить обязательные критерии в «Предпочтениях»." />
    </>
  )
}

export default function FeedPage() {
  const [params, setParams] = useSearchParams()
  const all = params.get('show') === 'all'
  const tab = (active) => `rounded-md px-3 py-1.5 text-sm ${active ? 'bg-blue-600 text-white' : 'border border-slate-300 bg-white text-slate-700'}`
  return (
    <div>
      <h1 className="mb-4 text-xl font-semibold">Лента вакансий</h1>
      <div role="tablist" className="mb-4 flex gap-2">
        <button role="tab" aria-selected={!all} onClick={() => setParams({})} className={tab(!all)}>
          Подходящие мне
        </button>
        <button role="tab" aria-selected={all} onClick={() => setParams({ show: 'all' })} className={tab(all)}>
          Все вакансии
        </button>
      </div>
      {all ? <AllVacancies /> : <BestMatches />}
    </div>
  )
}
