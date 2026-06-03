import { fetchApi } from './client'

interface ChatResponse {
  answer: string
  session_id: number
}

interface ChatSession {
  id: number
  title: string
  created_at: string
  updated_at: string
}

interface ChatMessageData {
  role: 'user' | 'bot'
  content: string
  created_at: string
}

export async function sendMessage(message: string, sessionId?: number): Promise<ChatResponse> {
  return fetchApi<ChatResponse>('/api/chat', {
    method: 'POST',
    body: JSON.stringify({ message, session_id: sessionId }),
  })
}

export async function getSessions(): Promise<ChatSession[]> {
  return fetchApi<ChatSession[]>('/api/chat/sessions')
}

export async function createSession(): Promise<{ id: number; title: string }> {
  return fetchApi('/api/chat/sessions', { method: 'POST' })
}

export async function deleteSession(id: number): Promise<void> {
  await fetchApi(`/api/chat/sessions/${id}`, { method: 'DELETE' })
}

export async function getMessages(sessionId: number): Promise<ChatMessageData[]> {
  return fetchApi<ChatMessageData[]>(`/api/chat/sessions/${sessionId}/messages`)
}
