import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api/client.js'
import { useAuth } from '../../auth/AuthContext.jsx'
import { buttonClass, inputClass } from './Card.jsx'

export default function NameForm() {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [name, setName] = useState(user.full_name || '')
  const [saved, setSaved] = useState(false)

  const mutation = useMutation({
    mutationFn: (full_name) => api('/me', { method: 'PATCH', body: JSON.stringify({ full_name }) }),
    onSuccess: (updated) => {
      setName(updated.full_name || '')
      setSaved(true)
      queryClient.invalidateQueries({ queryKey: ['me'] })
    },
  })

  function onSubmit(e) {
    e.preventDefault()
    setSaved(false)
    mutation.mutate(name)
  }

  return (
    <form onSubmit={onSubmit} className="mt-4 flex flex-col gap-2 border-t border-slate-100 pt-4">
      <label htmlFor="full_name" className="text-xs text-slate-500">
        Имя
      </label>
      <input
        id="full_name"
        maxLength={100}
        className={inputClass}
        value={name}
        onChange={(e) => {
          setName(e.target.value)
          setSaved(false)
        }}
      />
      <div className="flex items-center gap-3">
        <button type="submit" disabled={mutation.isPending} className={buttonClass}>
          Сохранить
        </button>
        {saved && (
          <span role="status" className="text-sm text-green-700">
            Сохранено
          </span>
        )}
        {mutation.isError && (
          <span role="alert" className="text-sm text-red-600">
            {mutation.error.message}
          </span>
        )}
      </div>
    </form>
  )
}
