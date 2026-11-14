import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { api } from '../../api/client.js'
import { useAuth } from '../../auth/AuthContext.jsx'
import { inputClass } from './Card.jsx'

export default function DeleteAccount() {
  const { logout } = useAuth()
  const [open, setOpen] = useState(false)
  const [password, setPassword] = useState('')

  const mutation = useMutation({
    mutationFn: () => api('/me', { method: 'DELETE', body: JSON.stringify({ password }) }),
    onSuccess: () => logout(), 
  })

  if (!open) {
    return (
      <>
        <p className="mb-3 text-sm text-slate-600">Аккаунт, резюме и все связанные данные будут удалены без возможности восстановления.</p>
        <button type="button" onClick={() => setOpen(true)} className="rounded-md border border-red-300 px-4 py-2 text-sm text-red-700">
          Удалить аккаунт
        </button>
      </>
    )
  }

  return (
    <form
      className="flex max-w-sm flex-col gap-2"
      onSubmit={(e) => {
        e.preventDefault()
        mutation.mutate()
      }}
    >
      <label htmlFor="delete_password" className="text-xs text-slate-500">
        Пароль для подтверждения
      </label>
      <input id="delete_password" type="password" autoComplete="current-password" className={inputClass} value={password} onChange={(e) => setPassword(e.target.value)} />
      {mutation.isError && (
        <p role="alert" className="text-sm text-red-600">
          {mutation.error.message}
        </p>
      )}
      <div className="flex gap-2">
        <button type="submit" disabled={!password || mutation.isPending} className="rounded-md bg-red-600 px-4 py-2 text-sm text-white disabled:opacity-60">
          Удалить навсегда
        </button>
        <button type="button" onClick={() => setOpen(false)} className="rounded-md border border-slate-300 px-4 py-2 text-sm">
          Отмена
        </button>
      </div>
    </form>
  )
}
