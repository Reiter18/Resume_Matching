import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client.js'
import { clearToken, getToken, setToken } from './token.js'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [token, setTokenState] = useState(getToken)
  const queryClient = useQueryClient()

  useEffect(() => {
    const sync = () => setTokenState(getToken())
    window.addEventListener('auth-change', sync)
    window.addEventListener('storage', sync)
    return () => {
      window.removeEventListener('auth-change', sync)
      window.removeEventListener('storage', sync)
    }
  }, [])

  const login = useCallback(async (email, password) => {
    const data = await api('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) })
    setToken(data.access_token)
  }, [])

  const register = useCallback(
    async (email, password) => {
      await api('/auth/register', { method: 'POST', body: JSON.stringify({ email, password }) })
      await login(email, password)
    },
    [login],
  )

  const logout = useCallback(() => {
    clearToken()
    queryClient.clear() 
  }, [queryClient])

  const { data: user, isLoading, isError, refetch } = useQuery({
    queryKey: ['me', token],
    queryFn: () => api('/me'),
    enabled: Boolean(token),
    retry: false,
  })

  const value = useMemo(
    () => ({ token, user, isLoading: Boolean(token) && isLoading, isError, refetch, login, register, logout }),
    [token, user, isLoading, isError, refetch, login, register, logout],
  )
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth нужно вызывать внутри AuthProvider')
  return ctx
}
