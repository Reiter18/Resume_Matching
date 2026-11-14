import { useState } from 'react'
import { useInfiniteQuery } from '@tanstack/react-query'
import { api } from '../api/client.js'
import { useDebouncedValue } from '../hooks/useDebouncedValue.js'
import Filters, { EMPTY } from './feed/Filters.jsx'
import VacancyList from './feed/VacancyList.jsx'

const PAGE = 20

function queryString(filters, offset) {
  const params = new URLSearchParams({ limit: PAGE, offset })
  for (const [key, value] of Object.entries(filters)) if (value) params.set(key, value)
  return params.toString()
}

export default function FeedPage() {
  const [filters, setFilters] = useState(EMPTY)
  const applied = JSON.parse(useDebouncedValue(JSON.stringify(filters), 300)) 

  const feed = useInfiniteQuery({
    queryKey: ['vacancies', applied],
    queryFn: ({ pageParam }) => api(`/vacancies?${queryString(applied, pageParam)}`),
    initialPageParam: 0,
    getNextPageParam: (last) => (last.offset + last.items.length < last.total ? last.offset + last.limit : undefined),
  })

  const pages = feed.data?.pages ?? []
  const items = [...new Map(pages.flatMap((p) => p.items).map((v) => [v.id, v])).values()]  

  return (
    <div>
      <h1 className="mb-4 text-xl font-semibold">Лента вакансий</h1>
      <Filters value={filters} onChange={setFilters} />
      {feed.isPending && <p className="text-sm text-slate-500">Загрузка…</p>}
      {feed.isError && (
        <p role="alert" className="text-sm text-red-600">
          {feed.error.message}
        </p>
      )}
      {feed.isSuccess && items.length === 0 && <p className="text-sm text-slate-500">Ничего не найдено. Измените фильтры.</p>}
      {items.length > 0 && (
        <>
          <p className="mb-2 text-xs text-slate-500">Найдено: {pages[0].total}</p>
          <VacancyList key={JSON.stringify(applied)} items={items} hasMore={feed.hasNextPage} loading={feed.isFetching} onMore={feed.fetchNextPage} />
        </>
      )}
    </div>
  )
}
