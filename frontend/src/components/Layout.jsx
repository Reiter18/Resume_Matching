import { NavLink, Outlet } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client.js'
import { useAuth } from '../auth/AuthContext.jsx'

const links = [
  ['/', 'Лента'],
  ['/profile', 'Профиль и резюме'],
  ['/preferences', 'Предпочтения'],
  ['/notifications', 'Уведомления'],
]

function Health() {
  const { data, isError } = useQuery({ queryKey: ['health'], queryFn: () => api('/health'), refetchInterval: 15_000 })
  const ok = data?.status === 'ok'
  return (
    <span className="text-xs text-slate-500" title="Состояние бэкенда">
      <span className={`mr-1 inline-block h-2 w-2 rounded-full ${ok ? 'bg-green-500' : isError ? 'bg-red-500' : 'bg-amber-500'}`} />
      {ok ? 'API работает' : isError ? 'API недоступен' : 'API: частично'}
    </span>
  )
}

export default function Layout() {
  const { user, logout } = useAuth()
  return (
    <div className="min-h-screen bg-slate-50 text-slate-800">
      <header className="flex h-14 items-center justify-between border-b border-slate-200 bg-white px-6">
        <b className="text-lg">JobMatch</b>
        <nav className="flex gap-6 text-sm">
          {links.map(([to, label]) => (
            <NavLink key={to} to={to} end={to === '/'} className={({ isActive }) => (isActive ? 'font-semibold text-blue-600' : 'text-slate-500')}>
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="flex items-center gap-4">
          <Health />
          <span className="text-xs text-slate-500">{user?.full_name || user?.email}</span>
          <button type="button" onClick={logout} className="rounded border border-slate-300 px-2 py-1 text-xs">
            Выйти
          </button>
        </div>
      </header>
      <main className="mx-auto max-w-5xl p-6">
        <Outlet />
      </main>
    </div>
  )
}
