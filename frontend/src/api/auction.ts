import { fetchApi } from './client'
import type { AuctionAlert } from '../types'

export async function getPendingAlerts() {
  return fetchApi<AuctionAlert[]>('/api/auction/pending')
}

export async function decideAuction(id: number, decision: string, price?: number, quantity?: number) {
  return fetchApi<{ message?: string }>(`/api/auction/decide/${id}`, {
    method: 'POST',
    body: JSON.stringify({ decision, price, quantity }),
  })
}
