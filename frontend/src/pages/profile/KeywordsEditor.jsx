import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api/client.js'
import { useDebouncedValue } from '../../hooks/useDebouncedValue.js'
import { buttonClass, inputClass } from './Card.jsx'

const MAX_SKILLS = 100

export default function KeywordsEditor({ resume }) {
  const queryClient = useQueryClient()
  const [skills, setSkills] = useState(resume.skills)
  const [unknown, setUnknown] = useState(() => new Set(resume.unknown_skills))
  const [input, setInput] = useState('')
  const [active, setActive] = useState(-1)
  const [focused, setFocused] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)

  const query = useDebouncedValue(input.trim(), 200)
  const suggestions = useQuery({
    queryKey: ['skill-suggest', query],
    queryFn: () => api(`/skills?q=${encodeURIComponent(query)}&limit=8`),
    enabled: query.length > 0,
    staleTime: 5 * 60_000,
  })
  const options = (query ? suggestions.data || [] : []).filter((s) => !skills.includes(s.name))
  const listOpen = focused && options.length > 0

  const dirty = skills.join('\n') !== resume.skills.join('\n')

  function add(names, unknownNames = []) {
    setSaved(false)
    const fresh = names.filter((n) => !skills.includes(n))
    if (skills.length + fresh.length > MAX_SKILLS) return setError(`Не больше ${MAX_SKILLS} ключевых слов`)
    setError('')
    setSkills([...skills, ...fresh])
    if (unknownNames.length) setUnknown(new Set([...unknown, ...unknownNames]))
    setInput('')
    setActive(-1)
  }

  async function addTyped(raw) {
    const names = raw.split(',').map((s) => s.trim()).filter(Boolean)
    if (!names.length) return
    try {
      const res = await api('/skills/normalize', { method: 'POST', body: JSON.stringify({ names }) })
      add(res.skills, res.unknown)
    } catch (e) {
      setError(e.message)
    }
  }

  function onKeyDown(e) {
    if (e.key === 'ArrowDown' && options.length) {
      e.preventDefault()
      setActive((i) => (i + 1) % options.length)
    } else if (e.key === 'ArrowUp' && options.length) {
      e.preventDefault()
      setActive((i) => (i <= 0 ? options.length - 1 : i - 1))
    } else if (e.key === 'Escape') {
      setFocused(false)
    } else if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault()
      if (e.key === 'Enter' && active >= 0 && options[active]) add([options[active].name])
      else addTyped(input)
    } else if (e.key === 'Backspace' && !input && skills.length) {
      setSaved(false)
      setSkills(skills.slice(0, -1))
    }
  }

  function remove(name) {
    setSaved(false)
    setSkills(skills.filter((s) => s !== name))
  }

  function reset() {
    setSkills(resume.skills)
    setUnknown(new Set(resume.unknown_skills))
    setError('')
    setSaved(false)
  }

  const save = useMutation({
    mutationFn: () => api('/resumes/me/skills', { method: 'PUT', body: JSON.stringify({ skills }) }),
    onSuccess: (updated) => {
      queryClient.setQueryData(['resume'], updated)
      setSkills(updated.skills)
      setUnknown(new Set(updated.unknown_skills))
      setError('')
      setSaved(true)
    },
  })

  return (
    <div className="mt-4 border-t border-slate-100 pt-4">
      <h3 className="mb-1 text-sm font-semibold">Ключевые слова</h3>
      <p className="mb-3 text-xs text-slate-500">
        По ним мы подбираем вакансии. Добавьте навыки, которых не хватает, и уберите лишние. Автоматическое извлечение из текста резюме
        появится на 5-й неделе.
      </p>

      {skills.length === 0 ? (
        <p className="mb-3 text-sm text-slate-500">Ключевых слов пока нет.</p>
      ) : (
        <ul className="mb-3 flex flex-wrap gap-2" aria-label="Ключевые слова резюме">
          {skills.map((name) => (
            <li
              key={name}
              title={unknown.has(name) ? 'Нет в словаре: совпадения с вакансиями могут не находиться' : undefined}
              className={`flex items-center gap-1 rounded-full border px-3 py-1 text-xs ${
                unknown.has(name) ? 'border-amber-400 bg-amber-50 text-amber-800' : 'border-blue-300 bg-blue-50 text-blue-800'
              }`}
            >
              {name}
              <button type="button" aria-label={`Удалить ${name}`} onClick={() => remove(name)} className="ml-1 leading-none">
                ×
              </button>
            </li>
          ))}
        </ul>
      )}

      <div className="relative max-w-md">
        <label htmlFor="skill-input" className="text-xs text-slate-500">
          Добавить ключевое слово
        </label>
        <input
          id="skill-input"
          role="combobox"
          aria-expanded={listOpen}
          aria-controls="skill-options"
          aria-autocomplete="list"
          autoComplete="off"
          placeholder="например, Python или Docker"
          className={`${inputClass} mt-1`}
          value={input}
          onChange={(e) => {
            setInput(e.target.value)
            setActive(-1)
          }}
          onKeyDown={onKeyDown}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
        />
        {listOpen && (
          <ul id="skill-options" role="listbox" className="absolute z-10 mt-1 w-full rounded-md border border-slate-200 bg-white text-sm shadow">
            {options.map((s, i) => (
              <li
                key={s.name}
                role="option"
                aria-selected={i === active}
                onMouseDown={(e) => {
                  e.preventDefault() 
                  add([s.name])
                }}
                className={`flex cursor-pointer justify-between px-3 py-2 ${i === active ? 'bg-blue-50' : ''}`}
              >
                <span>
                  {s.name}
                  {s.matched_alias && <span className="ml-2 text-xs text-slate-400">({s.matched_alias})</span>}
                </span>
                <span className="text-xs text-slate-400">{s.category}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {error && (
        <p role="alert" className="mt-2 text-sm text-red-600">
          {error}
        </p>
      )}
      {save.isError && (
        <p role="alert" className="mt-2 text-sm text-red-600">
          {save.error.message}
        </p>
      )}

      <div className="mt-3 flex flex-wrap items-center gap-3">
        <button type="button" className={buttonClass} disabled={!dirty || save.isPending} onClick={() => save.mutate()}>
          Сохранить слова
        </button>
        {dirty && (
          <>
            <button type="button" onClick={reset} className="text-sm text-slate-600 underline">
              Отменить изменения
            </button>
            <span className="text-xs text-amber-700">Есть несохранённые изменения</span>
          </>
        )}
        {saved && !dirty && (
          <span role="status" className="text-sm text-green-700">
            Сохранено
          </span>
        )}
      </div>
    </div>
  )
}
