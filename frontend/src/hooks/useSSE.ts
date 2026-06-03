import { useEffect, useRef } from 'react'

export function useSSE(url: string, onMessage: (data: unknown) => void) {
  const onMessageRef = useRef(onMessage)
  onMessageRef.current = onMessage

  useEffect(() => {
    const source = new EventSource(url)
    source.onmessage = (e) => {
      try {
        onMessageRef.current(JSON.parse(e.data))
      } catch {}
    }
    source.onerror = () => {
      source.close()
      setTimeout(() => {
        const retry = new EventSource(url)
        retry.onmessage = source.onmessage
      }, 5000)
    }
    return () => source.close()
  }, [url])
}
