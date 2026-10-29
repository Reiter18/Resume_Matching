import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from './AuthContext.jsx'

export default function ProtectedRoute() {
  const { token, user, isLoading, isError, refetch } = useAuth()
  const location = useLocation()

  if (!token) return <Navigate to="/login" replace state={{ from: location }} />
  if (isLoading) return <p className="p-6 text-sm text-slate-500">Загрузка…</p>
  if (isError || !user) {
    return (
      <div className="p-6 text-sm">
        <p className="text-red-600">Не удалось загрузить профиль. Проверьте соединение.</p>
        <button className="mt-2 rounded border border-slate-300 bg-white px-3 py-1" onClick={() => refetch()}>
          Повторить
        </button>
      </div>
    )
  }
  return <Outlet />
}
