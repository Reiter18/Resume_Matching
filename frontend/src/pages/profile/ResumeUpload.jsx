import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api/client.js'
import { buttonClass } from './Card.jsx'

export const ALLOWED_EXTENSIONS = ['.pdf', '.docx', '.txt']
export const MAX_BYTES = 5 * 1024 * 1024
const MIN_TEXT = 30


export function validateFile(file) {
  const name = file.name.toLowerCase()
  if (!ALLOWED_EXTENSIONS.some((ext) => name.endsWith(ext))) return 'Поддерживаются файлы PDF, DOCX и TXT'
  if (file.size === 0) return 'Файл пустой'
  if (file.size > MAX_BYTES) return 'Файл больше 5 МБ'
  return ''
}

export default function ResumeUpload({ onUploaded }) {
  const queryClient = useQueryClient()
  const [mode, setMode] = useState('file')
  const [dragging, setDragging] = useState(false)
  const [problem, setProblem] = useState('')
  const [text, setText] = useState('')

  function done(resume) {
    queryClient.setQueryData(['resume'], resume)
    queryClient.removeQueries({ queryKey: ['resume-text'] })
    setProblem('')
    setText('')
    onUploaded?.(resume)
  }

  const upload = useMutation({
    mutationFn: (file) => {
      const body = new FormData()
      body.append('file', file)
      return api('/resumes', { method: 'POST', body })
    },
    onSuccess: done,
  })
  const paste = useMutation({
    mutationFn: () => api('/resumes/text', { method: 'POST', body: JSON.stringify({ text }) }),
    onSuccess: done,
  })

  function pick(file) {
    if (!file) return
    const message = validateFile(file)
    setProblem(message)
    if (!message) upload.mutate(file)
  }

  function submitText(e) {
    e.preventDefault()
    const message = text.trim().length < MIN_TEXT ? `Вставьте текст резюме (не короче ${MIN_TEXT} символов)` : ''
    setProblem(message)
    if (!message) paste.mutate()
  }

  const error = problem || (mode === 'file' ? upload.error?.message : paste.error?.message)
  const busy = upload.isPending || paste.isPending

  return (
    <div className="flex flex-col gap-3">
      <div className="flex gap-4 text-sm">
        {[
          ['file', 'Загрузить файл'],
          ['text', 'Вставить текстом'],
        ].map(([key, label]) => (
          <button
            key={key}
            type="button"
            aria-pressed={mode === key}
            onClick={() => {
              setMode(key)
              setProblem('')
            }}
            className={mode === key ? 'border-b-2 border-blue-600 pb-1 font-semibold' : 'pb-1 text-slate-500'}
          >
            {label}
          </button>
        ))}
      </div>

      {mode === 'file' ? (
        <label
          htmlFor="resume-file"
          data-testid="dropzone"
          onDragOver={(e) => {
            e.preventDefault()
            setDragging(true)
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault()
            setDragging(false)
            pick(e.dataTransfer?.files?.[0])
          }}
          className={`flex cursor-pointer flex-col items-center gap-1 rounded-lg border-2 border-dashed px-4 py-8 text-center text-sm ${
            dragging ? 'border-blue-500 bg-blue-50' : 'border-slate-300 text-slate-500'
          }`}
        >
          <span>{busy ? 'Загружаем…' : 'Перетащите файл сюда или выберите на компьютере'}</span>
          <span className="text-xs">PDF, DOCX или TXT, до 5 МБ</span>
          <input
            id="resume-file"
            type="file"
            accept=".pdf,.docx,.txt"
            disabled={busy}
            className="sr-only"
            onChange={(e) => {
              pick(e.target.files?.[0])
              e.target.value = '' 
            }}
          />
        </label>
      ) : (
        <form onSubmit={submitText} className="flex flex-col gap-2">
          <label htmlFor="resume-text" className="text-xs text-slate-500">
            Текст резюме
          </label>
          <textarea
            id="resume-text"
            rows={8}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:border-blue-500"
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
          <div className="flex items-center gap-3">
            <button type="submit" disabled={busy} className={buttonClass}>
              {busy ? 'Сохраняем…' : 'Сохранить текст'}
            </button>
            <span className="text-xs text-slate-400">{text.trim().length} символов</span>
          </div>
        </form>
      )}

      {error && (
        <p role="alert" className="text-sm text-red-600">
          {error}
        </p>
      )}
    </div>
  )
}
