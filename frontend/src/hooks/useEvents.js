import { useEffect, useRef } from 'react'
import { getToken } from '../auth/token.js'

const RETRY_MS = 3000

export function useEvents(onEvent) {
  const handler = useRef(onEvent)
  useEffect(() => {
    handler.current = onEvent
  })

  useEffect(() => {
    const controller = new AbortController()
    let timer

    function emit(message) {
      const data = message
        .split('\n')
        .filter((line) => line.startsWith('data: '))
        .map((line) => line.slice(6))
        .join('\n')
      if (!data) return 
      try {
        handler.current(JSON.parse(data))
      } catch {
        // Повреждённое сообщение пропускаем.
      }
    }

    async function listen() {
      try {
        const res = await fetch('/api/events', { headers: { Authorization: `Bearer ${getToken()}` }, signal: controller.signal })
        if (!res.ok || !res.body) return 
        const reader = res.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''
        for (;;) {
          const { done, value } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })
          const messages = buffer.split('\n\n')
          buffer = messages.pop() 
          messages.forEach(emit)
        }
      } catch {
        // При сетевом сбое поток переподключится ниже.
      }
      if (!controller.signal.aborted) timer = setTimeout(listen, RETRY_MS)
    }

    listen()
    return () => {
      controller.abort()
      clearTimeout(timer)
    }
  }, [])
}
