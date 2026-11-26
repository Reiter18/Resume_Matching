import { useCallback, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { useEvents } from '../hooks/useEvents.js'

export default function Notifications() {
  const queryClient = useQueryClient()
  const [news, setNews] = useState(null)

  useEvents(
    useCallback(
      (event) => {
        if (event.type !== 'new_matches' && event.type !== 'matches_refreshed') return
        queryClient.invalidateQueries({ queryKey: ['/matches'] }) 
        queryClient.invalidateQueries({ queryKey: ['match'] }) 
        if (event.type === 'new_matches') setNews(event)
      },
      [queryClient],
    ),
  )

  if (!news) return null
  const close = () => setNews(null)
  return (
    <aside role="status" className="fixed bottom-4 right-4 w-72 rounded-lg border border-slate-200 bg-white p-4 text-sm shadow-lg">
      <p className="font-semibold">{news.count === 1 ? 'Новая подходящая вакансия' : `Новых подходящих вакансий: ${news.count}`}</p>
      <Link to={`/vacancies/${news.best.id}`} onClick={close} className="mt-1 block truncate text-blue-700 underline">
        {news.best.title}
      </Link>
      <p className="text-xs text-slate-500">Лучшая оценка: {news.best.score}%</p>
      <div className="mt-2 flex gap-3 text-xs">
        <Link to="/" onClick={close} className="underline">
          В ленту
        </Link>
        <button type="button" onClick={close} className="text-slate-500 underline">
          Закрыть
        </button>
      </div>
    </aside>
  )
}
