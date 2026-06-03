import { fetchApi } from './client'

export async function getMode() {
  return fetchApi<{ mode: string }>('/api/settings/mode')
}

export async function setMode(mode: string) {
  return fetchApi<{ message: string }>('/api/settings/mode', {
    method: 'POST',
    body: JSON.stringify({ mode }),
  })
}

export async function refreshToken() {
  return fetchApi<{ message: string }>('/api/settings/token-refresh', { method: 'POST' })
}
