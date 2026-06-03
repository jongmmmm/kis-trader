import { fetchApi } from './client'
import type { Order } from '../types'

export async function getOrders(mode = '', trigger = '') {
  const params = new URLSearchParams()
  if (mode) params.set('mode', mode)
  if (trigger) params.set('trigger', trigger)
  const q = params.toString()
  return fetchApi<Order[]>(`/orders/api/orders${q ? '?' + q : ''}`)
}
