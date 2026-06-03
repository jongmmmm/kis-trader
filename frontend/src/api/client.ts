export async function fetchApi<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    ...options,
    credentials: 'include',
    headers: {
      ...(options?.method && options.method !== 'GET' ? { 'Content-Type': 'application/json' } : {}),
      ...options?.headers,
    },
  })
  if (!res.ok) {
    const data = await res.json().catch(() => ({ msg: `HTTP ${res.status}` }))
    throw new Error(data.msg || data.error || `HTTP ${res.status}`)
  }
  return res.json()
}
