import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ApiError, api } from '../../api/client.js'

const LANGUAGES = { ru: 'русский', en: 'английский', mixed: 'смешанный' }

function useResume() {
  return useQuery({
    queryKey: ['resume'],
    retry: false,
    queryFn: async () => {
      try {
        return await api('/resumes/me')
      } catch (e) {
        if (e instanceof ApiError && e.status === 404) return null
        throw e
      }
    },
  })
}

export default function ResumeCard() {
  const queryClient = useQueryClient()
  const resume = useResume()
  const [showFull, setShowFull] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)

  const fullText = useQuery({ queryKey: ['resume-text'], queryFn: () => api('/resumes/me/text'), enabled: showFull && Boolean(resume.data), retry: false })
  const remove = useMutation({
    mutationFn: () => api('/resumes/me', { method: 'DELETE' }),
    onSuccess: () => {
      setConfirmDelete(false)
      setShowFull(false)
      queryClient.removeQueries({ queryKey: ['resume-text'] })
      queryClient.invalidateQueries({ queryKey: ['resume'] })
    },
  })

  if (resume.isLoading) return <p className="text-sm text-slate-500">Загрузка…</p>
  if (resume.isError) return <p className="text-sm text-red-600">Не удалось загрузить резюме</p>
  if (resume.data === null) return <p className="text-sm text-slate-500">Резюме пока не загружено. Загрузка появится на 4-й неделе.</p>

  const r = resume.data
  return (
    <div className="text-sm">
      <p>
        <b>{r.original_filename || 'Резюме'}</b>
        <span className="ml-2 text-slate-500">
          {r.char_count} символов · язык: {LANGUAGES[r.language] || 'не определён'}
        </span>
      </p>
      {showFull ? (
        <pre className="mt-3 max-h-96 overflow-auto whitespace-pre-wrap rounded bg-slate-50 p-3 text-xs">
          {fullText.isLoading ? 'Загрузка…' : fullText.isError ? 'Не удалось загрузить текст' : fullText.data?.text}
        </pre>
      ) : (
        <pre className="mt-3 max-h-64 overflow-auto whitespace-pre-wrap rounded bg-slate-50 p-3 text-xs">{r.preview}</pre>
      )}
      <div className="mt-3 flex flex-wrap items-center gap-3">
        <button type="button" onClick={() => setShowFull((v) => !v)} className="text-blue-600 underline">
          {showFull ? 'Свернуть' : 'Показать полный текст'}
        </button>
        {!confirmDelete ? (
          <button type="button" onClick={() => setConfirmDelete(true)} className="text-red-600 underline">
            Удалить резюме
          </button>
        ) : (
          <span className="flex items-center gap-2">
            Точно удалить?
            <button type="button" onClick={() => remove.mutate()} disabled={remove.isPending} className="rounded bg-red-600 px-2 py-1 text-xs text-white">
              Да, удалить
            </button>
            <button type="button" onClick={() => setConfirmDelete(false)} className="rounded border border-slate-300 px-2 py-1 text-xs">
              Отмена
            </button>
          </span>
        )}
      </div>
    </div>
  )
}
