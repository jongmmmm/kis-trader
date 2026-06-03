import { fetchApi } from './client'
import type { EsgScore, AuditLog, InvestLimit } from '../types'

export async function getEsgScore(stockCode: string) {
  return fetchApi<EsgScore>(`/api/esg/${stockCode}`)
}

export async function getEsgList() {
  return fetchApi<EsgScore[]>('/api/esg/list')
}

export async function getAuditLogs() {
  return fetchApi<AuditLog[]>('/api/audit-logs')
}

export async function getInvestLimit() {
  return fetchApi<InvestLimit>('/api/invest-limit')
}

export async function setInvestLimit(data: InvestLimit) {
  return fetchApi<{ message: string }>('/api/invest-limit', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}
