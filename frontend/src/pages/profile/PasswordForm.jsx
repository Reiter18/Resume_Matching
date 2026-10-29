import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { api } from '../../api/client.js'
import { buttonClass, inputClass } from './Card.jsx'

export default function PasswordForm() {
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [repeat, setRepeat] = useState('')
  const [problem, setProblem] = useState('')
  const [done, setDone] = useState(false)

  const mutation = useMutation({
    mutationFn: () =>
      api('/me/password', { method: 'POST', body: JSON.stringify({ current_password: current, new_password: next }) }),
    onSuccess: () => {
      setCurrent('')
      setNext('')
      setRepeat('')
      setDone(true)
    },
  })

  function validate() {
    if (!current) return 'Введите текущий пароль'
    if (next.length < 8) return 'Новый пароль не короче 8 символов'
    if (next !== repeat) return 'Пароли не совпадают'
    if (next === current) return 'Новый пароль совпадает с текущим'
    return ''
  }

  function onSubmit(e) {
    e.preventDefault()
    setDone(false)
    const message = validate()
    setProblem(message)
    if (!message) mutation.mutate()
  }

  const fields = [
    ['current_password', 'Текущий пароль', current, setCurrent, 'current-password'],
    ['new_password', 'Новый пароль', next, setNext, 'new-password'],
    ['repeat_password', 'Повторите новый пароль', repeat, setRepeat, 'new-password'],
  ]

  return (
    <form onSubmit={onSubmit} noValidate className="flex max-w-sm flex-col gap-2">
      {fields.map(([id, label, value, set, autoComplete]) => (
        <div key={id} className="flex flex-col gap-1">
          <label htmlFor={id} className="text-xs text-slate-500">
            {label}
          </label>
          <input id={id} type="password" autoComplete={autoComplete} className={inputClass} value={value} onChange={(e) => set(e.target.value)} />
        </div>
      ))}
      {(problem || mutation.isError) && (
        <p role="alert" className="text-sm text-red-600">
          {problem || mutation.error.message}
        </p>
      )}
      {done && (
        <p role="status" className="text-sm text-green-700">
          Пароль изменён
        </p>
      )}
      <div>
        <button type="submit" disabled={mutation.isPending} className={buttonClass}>
          Сменить пароль
        </button>
      </div>
    </form>
  )
}
