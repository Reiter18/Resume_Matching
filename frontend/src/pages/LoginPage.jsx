import { useState } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext.jsx'

const inputClass = 'w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:border-blue-500'

export default function LoginPage() {
  const { token, login, register } = useAuth()
  const location = useLocation()
  const [mode, setMode] = useState('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [showPassword, setShowPassword] = useState(false)

  const isRegister = mode === 'register'
  const from = location.state?.from?.pathname || '/'
  if (token) return <Navigate to={from} replace />

  function validate() {
    if (!/^\S+@\S+\.\S+$/.test(email.trim())) return 'Введите корректный email'
    if (isRegister && password.length < 8) return 'Пароль должен быть не короче 8 символов'
    if (!password) return 'Введите пароль'
    return ''
  }

  async function onSubmit(e) {
    e.preventDefault()
    const problem = validate()
    if (problem) return setError(problem)
    setError('')
    setBusy(true)
    try {
      await (isRegister ? register(email.trim(), password) : login(email.trim(), password))
    } catch (err) {
      setError(err.message || 'Что-то пошло не так')
      setBusy(false)
    }
  }

  function switchMode(next) {
    setMode(next)
    setError('')
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 p-6">
      <div className="w-full max-w-sm rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <h1 className="mb-4 text-lg font-semibold">JobMatch</h1>
        <div className="mb-5 flex gap-4 text-sm">
          {[
            ['login', 'Вход'],
            ['register', 'Регистрация'],
          ].map(([key, label]) => (
            <button
              key={key}
              type="button"
              aria-pressed={mode === key}
              onClick={() => switchMode(key)}
              className={mode === key ? 'border-b-2 border-blue-600 pb-1 font-semibold' : 'pb-1 text-slate-500'}
            >
              {label}
            </button>
          ))}
        </div>
        <form onSubmit={onSubmit} noValidate className="flex flex-col gap-3">
          <label htmlFor="email" className="text-xs text-slate-500">
            Email
          </label>
          <input id="email" type="email" autoComplete="email" className={inputClass} value={email} onChange={(e) => setEmail(e.target.value)} />
          <label htmlFor="password" className="text-xs text-slate-500">
            Пароль
          </label>
          <input
            id="password"
            type={showPassword ? 'text' : 'password'}
            autoComplete={isRegister ? 'new-password' : 'current-password'}
            className={inputClass}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <div className="flex items-center justify-between text-xs text-slate-500">
            <span>{isRegister ? 'Не короче 8 символов' : ''}</span>
            <button type="button" aria-pressed={showPassword} onClick={() => setShowPassword((v) => !v)} className="underline">
              {showPassword ? 'Скрыть пароль' : 'Показать пароль'}
            </button>
          </div>
          {error && (
            <p role="alert" className="text-sm text-red-600">
              {error}
            </p>
          )}
          <button type="submit" disabled={busy} className="mt-1 rounded-md bg-blue-600 py-2 text-sm text-white disabled:opacity-60">
            {busy ? 'Подождите…' : isRegister ? 'Создать аккаунт' : 'Войти'}
          </button>
        </form>
        <p className="mt-4 text-xs text-slate-500">Резюме — персональные данные: видите только вы.</p>
      </div>
    </div>
  )
}
