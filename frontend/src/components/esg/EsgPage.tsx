import { useState, useEffect } from 'react'
import { getEsgList, getAuditLogs, getInvestLimit, setInvestLimit } from '../../api/esg'
import type { EsgScore, AuditLog, InvestLimit } from '../../types'

const GRADE_COLORS: Record<string, string> = {
  'S': '#2ecc71', 'A+': '#27ae60', 'A': '#3498db',
  'B+': '#f39c12', 'B': '#e67e22', 'C': '#e74c3c', 'D': '#95a5a6',
}

function GradeBadge({ grade }: { grade: string }) {
  if (!grade) return <span className="badge bg-secondary">N/A</span>
  return <span className="badge" style={{ background: GRADE_COLORS[grade] || '#aaa', fontSize: 12 }}>{grade}</span>
}

export default function EsgPage() {
  const [tab, setTab] = useState<'esg' | 'limit' | 'audit'>('esg')
  const [esgList, setEsgList] = useState<EsgScore[]>([])
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([])
  const [limit, setLimit] = useState<InvestLimit>({ daily_limit: 0, monthly_limit: 0, per_order_limit: 0, esg_min_grade: '' })
  const [msg, setMsg] = useState('')

  useEffect(() => {
    if (tab === 'esg') getEsgList().then(setEsgList).catch(() => {})
    if (tab === 'audit') getAuditLogs().then(setAuditLogs).catch(() => {})
    if (tab === 'limit') getInvestLimit().then(setLimit).catch(() => {})
  }, [tab])

  const saveLimit = async () => {
    try {
      const r = await setInvestLimit(limit)
      setMsg(r.message)
      setTimeout(() => setMsg(''), 3000)
    } catch { setMsg('저장 실패') }
  }

  return (
    <div>
      <h4 className="fw-bold mb-3">ESG 경영 관리</h4>

      <ul className="nav nav-tabs mb-3">
        <li className="nav-item">
          <button className={`nav-link ${tab === 'esg' ? 'active' : ''}`} onClick={() => setTab('esg')}>ESG 등급</button>
        </li>
        <li className="nav-item">
          <button className={`nav-link ${tab === 'limit' ? 'active' : ''}`} onClick={() => setTab('limit')}>투자 한도</button>
        </li>
        <li className="nav-item">
          <button className={`nav-link ${tab === 'audit' ? 'active' : ''}`} onClick={() => setTab('audit')}>감사 로그</button>
        </li>
      </ul>

      {/* ESG 등급 탭 */}
      {tab === 'esg' && (
        <div className="table-responsive">
          <table className="table table-hover">
            <thead><tr>
              <th>종목코드</th><th>종목명</th><th>종합</th><th>환경(E)</th><th>사회(S)</th><th>지배구조(G)</th><th>점수</th><th>평가년도</th>
            </tr></thead>
            <tbody>
              {esgList.map(e => (
                <tr key={e.stock_code}>
                  <td>{e.stock_code}</td>
                  <td className="fw-bold">{e.stock_name}</td>
                  <td><GradeBadge grade={e.total_grade} /></td>
                  <td><GradeBadge grade={e.env_grade} /></td>
                  <td><GradeBadge grade={e.social_grade} /></td>
                  <td><GradeBadge grade={e.gov_grade} /></td>
                  <td>{e.score}</td>
                  <td>{e.data_year}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* 투자 한도 탭 */}
      {tab === 'limit' && (
        <div style={{ maxWidth: 500 }}>
          <div className="mb-3">
            <label className="form-label fw-bold">일일 매수 한도 (원)</label>
            <input type="number" className="form-control" value={limit.daily_limit} min={0} step={100000}
              onChange={e => setLimit({ ...limit, daily_limit: Number(e.target.value) })} />
            <div className="form-text">0 = 무제한</div>
          </div>
          <div className="mb-3">
            <label className="form-label fw-bold">월간 매수 한도 (원)</label>
            <input type="number" className="form-control" value={limit.monthly_limit} min={0} step={1000000}
              onChange={e => setLimit({ ...limit, monthly_limit: Number(e.target.value) })} />
            <div className="form-text">0 = 무제한</div>
          </div>
          <div className="mb-3">
            <label className="form-label fw-bold">건당 매수 한도 (원)</label>
            <input type="number" className="form-control" value={limit.per_order_limit} min={0} step={100000}
              onChange={e => setLimit({ ...limit, per_order_limit: Number(e.target.value) })} />
            <div className="form-text">0 = 무제한</div>
          </div>
          <div className="mb-3">
            <label className="form-label fw-bold">ESG 최소 등급 필터</label>
            <select className="form-select" value={limit.esg_min_grade}
              onChange={e => setLimit({ ...limit, esg_min_grade: e.target.value })}>
              <option value="">미적용</option>
              <option value="S">S</option>
              <option value="A+">A+</option>
              <option value="A">A</option>
              <option value="B+">B+</option>
              <option value="B">B</option>
            </select>
            <div className="form-text">설정한 등급 미만 종목은 매수 차단</div>
          </div>
          <button className="btn btn-primary" onClick={saveLimit}>저장</button>
          {msg && <div className="alert alert-success mt-2">{msg}</div>}
        </div>
      )}

      {/* 감사 로그 탭 */}
      {tab === 'audit' && (
        <div className="table-responsive">
          <table className="table table-sm table-hover" style={{ fontSize: 13 }}>
            <thead><tr>
              <th>시간</th><th>구분</th><th>종목</th><th>가격</th><th>수량</th><th>ESG</th><th>모드</th><th>사유</th>
            </tr></thead>
            <tbody>
              {auditLogs.map(l => (
                <tr key={l.id} className={l.action === 'blocked' ? 'table-danger' : ''}>
                  <td>{l.created_at.replace('T', ' ').slice(0, 19)}</td>
                  <td>
                    <span className={`badge ${l.action === 'buy' ? 'bg-primary' : l.action === 'sell' ? 'bg-danger' : 'bg-warning text-dark'}`}>
                      {l.action === 'buy' ? '매수' : l.action === 'sell' ? '매도' : l.action === 'blocked' ? '차단' : l.action}
                    </span>
                  </td>
                  <td>{l.stock_name || l.stock_code}</td>
                  <td>{l.price.toLocaleString()}원</td>
                  <td>{l.quantity}주</td>
                  <td><GradeBadge grade={l.esg_grade} /></td>
                  <td>{l.mode === 'real' ? '실전' : '모의'}</td>
                  <td style={{ maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                    title={l.reason}>{l.reason}</td>
                </tr>
              ))}
              {auditLogs.length === 0 && <tr><td colSpan={8} className="text-center text-muted py-3">감사 로그가 없습니다</td></tr>}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
