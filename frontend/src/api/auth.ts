import { fetchApi } from './client'
import type { User } from '../types'

export async function apiLogin(username: string, password: string, remember: boolean) {
  return fetchApi<{ success: boolean; user: User; msg?: string }>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password, remember }),
  })
}

export async function apiSignup(data: {
  username: string; password: string; password2: string;
  name: string; phone: string; email: string; birth_date: string; login_method: string
}) {
  return fetchApi<{ success: boolean; redirect?: string; errors?: string[] }>('/api/auth/signup', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function apiLogout() {
  return fetchApi<{ success: boolean }>('/api/auth/logout', { method: 'POST' })
}

export async function apiMe() {
  return fetchApi<{ authenticated: boolean; user: User }>('/api/auth/me')
}

export async function checkUsername(username: string) {
  return fetchApi<{ available: boolean; msg: string }>(`/api/auth/check-username?username=${encodeURIComponent(username)}`)
}
