import { useEffect, useState } from 'react'
import VacancyCard from './VacancyCard.jsx'

export const ROW = 120 
const HEIGHT = 600 
const OVERSCAN = 3 

export default function VacancyList({ items, hasMore, loading, onMore }) {
  const [top, setTop] = useState(0)
  const first = Math.max(0, Math.floor(top / ROW) - OVERSCAN)
  const last = Math.min(items.length, Math.ceil((top + HEIGHT) / ROW) + OVERSCAN)
  const needMore = hasMore && !loading && last >= items.length - 2

  useEffect(() => {
    if (needMore) onMore()
  }, [needMore, onMore])

  return (
    <div role="region" aria-label="Список вакансий" onScroll={(e) => setTop(e.currentTarget.scrollTop)} className="overflow-y-auto" style={{ height: HEIGHT }}>
      <ul className="relative" style={{ height: items.length * ROW }}>
        {items.slice(first, last).map((v, i) => (
          <li key={v.id} className="absolute inset-x-0" style={{ top: (first + i) * ROW, height: ROW, paddingBottom: 8 }}>
            <VacancyCard v={v} />
          </li>
        ))}
      </ul>
    </div>
  )
}
