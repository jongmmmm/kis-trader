import { fetchApi } from './client'
import type { Strategy, ChartData, ChartEvent, BacktestResult } from '../types'

export async function getStrategies() {
  return fetchApi<Strategy[]>('/strategies/api/strategies')
}

export async function createStrategy(data: Partial<Strategy>) {
  return fetchApi<Strategy>('/strategies/api/strategies', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function deleteStrategy(id: number) {
  return fetchApi<{ success: boolean }>(`/strategies/api/strategies/${id}`, { method: 'DELETE' })
}

export async function toggleStrategy(id: number) {
  return fetchApi<{ success: boolean }>(`/strategies/api/strategies/${id}/toggle`, { method: 'POST' })
}

export async function getChartData(id: number, period: string) {
  return fetchApi<ChartData>(`/strategies/api/strategies/${id}/chart?period=${period}`)
}

export async function getEvents(id: number, period: string) {
  return fetchApi<{ events: ChartEvent[] }>(`/strategies/api/strategies/${id}/events?period=${period}`)
}

export async function runBacktest(id: number, period: string, capital: number) {
  return fetchApi<BacktestResult>(`/strategies/api/strategies/${id}/backtest?period=${period}&capital=${capital}`)
}

export async function runAiAnalysis(id: number) {
  return fetchApi<Record<string, unknown>>(`/strategies/api/strategies/${id}/ai-analyze`)
}
