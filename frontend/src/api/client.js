import { clearToken, getToken } from '../auth/token.js'

export class ApiError extends Error {
  constructor(status, message) {
    super(message)
    this.status = status
  }
}

function errorMessage(status, body) {
  if (typeof body?.detail === 'string') return body.detail
  if (status === 422) return 'Проверьте введённые данные'
  if (status === 429) return 'Слишком много запросов, попробуйте позже'
  return `Ошибка ${status}`
}

export async function api(path, options = {}) {
  const token = getToken()
  const isForm = options.body instanceof FormData
  const headers = {
    ...(options.body && !isForm ? { 'Content-Type': 'application/json' } : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers || {}),
  }
  const res = await fetch(`/api${path}`, { ...options, headers })
  if (!res.ok) {
    let body = null
    try {
      body = await res.json()
    } catch {
      // Игнорирование ошибки
    }
    if (res.status === 401 && token && !path.startsWith('/auth/')) clearToken()
    throw new ApiError(res.status, errorMessage(res.status, body))
  }
  return res.status === 204 ? null : res.json()
}
