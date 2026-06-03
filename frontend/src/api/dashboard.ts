import { fetchApi } from './client'
import type { MarketPricesResponse, BalanceItem, RankItem, OverseasStock } from '../types'

export async function getMarketPrices(extra = '') {
  const q = extra ? `?extra=${extra}` : ''
  return fetchApi<MarketPricesResponse>(`/api/market-prices${q}`)
}

export async function getBalance() {
  return fetchApi<{ balance: BalanceItem[] }>('/api/balance')
}

export async function getMarketRanking() {
  return fetchApi<{ stocks: RankItem[] }>('/api/market-ranking')
}

export async function getStockPrice(code: string) {
  return fetchApi<Record<string, unknown>>(`/api/stock-price/${code}`)
}

export async function getOverseasPrices(stocks: string) {
  return fetchApi<{ stocks: OverseasStock[] }>(`/api/overseas-prices?stocks=${stocks}`)
}

export async function getOverseasBalance() {
  return fetchApi<{ balance: BalanceItem[] }>('/api/overseas-balance')
}

export async function getOverseasRanking(excd: string) {
  return fetchApi<{ stocks: RankItem[] }>(`/api/overseas-ranking?excd=${excd}`)
}
