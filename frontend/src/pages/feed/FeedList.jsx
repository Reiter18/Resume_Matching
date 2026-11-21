import { keepPreviousData, useInfiniteQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../../api/client.js'
import VacancyList from './VacancyList.jsx'

const PAGE = 20

function queryString(filters, offset) {
  const params = new URLSearchParams({ limit: PAGE, offset })
  for (const [key, value] of Object.entries(filters)) if (value) params.set(key, value)
  return params.toString()
}

export default function FeedList({ path, filters, emptyText }) {
  const feed = useInfiniteQuery({
    queryKey: [path, filters],
    queryFn: ({ pageParam }) => api(`${path}?${queryString(filters, pageParam)}`),
    initialPageParam: 0,
    placeholderData: keepPreviousData, 
    refetchOnMount: 'always', 
    refetchInterval: (query) => (query.state.data?.pages[0]?.pending ? 3000 : false), 
    getNextPageParam: (last) => (last.offset + last.items.length < last.total ? last.offset + last.limit : undefined),
  })

  const pages = feed.data?.pages ?? []
  const rows = [...new Map(pages.flatMap((p) => p.items).map((r) => [(r.vacancy ?? r).id, r])).values()] 
  const items = rows.map((r) => (r.vacancy ? { ...r.vacancy, score: r.score } : r))

  return (
    <>
      {feed.isPending && <p className="text-sm text-slate-500">Загрузка…</p>}
      {feed.isError && (
        <p role="alert" className="text-sm text-red-600">
          {feed.error.message}{' '}
          {feed.error.status === 404 && (
            <Link to="/profile" className="underline">
              Загрузить резюме
            </Link>
          )}
        </p>
      )}
      {pages[0]?.pending && <p className="text-sm text-slate-500">Подбираем вакансии, это займёт несколько секунд…</p>}
      {feed.isSuccess && !feed.isPlaceholderData && items.length === 0 && !pages[0]?.pending && <p className="text-sm text-slate-500">{emptyText}</p>}
      {items.length > 0 && (
        <div className={feed.isPlaceholderData ? 'opacity-50' : undefined}>
          <p className="mb-2 text-xs text-slate-500">Найдено: {pages[0].total}</p>
          <VacancyList key={JSON.stringify([path, filters])} items={items} hasMore={feed.hasNextPage} loading={feed.isFetching} onMore={feed.fetchNextPage} />
        </div>
      )}
    </>
  )
}
