import { useState, useRef } from 'react'
import { usePolling } from '../../hooks/usePolling'
import { getMarketRanking, getOverseasRanking } from '../../api/dashboard'
import type { RankItem } from '../../types'
import { fmt, fmtF, fmtVol, fmtO, fmtVolUS, chgClass, signStr } from '../../utils/format'

const tabs = [
  { key: 'domestic', label: '국내', icon: 'fa-flag' },
  { key: 'NAS', label: 'NASDAQ' },
  { key: 'NYS', label: 'NYSE' },
  { key: 'AMS', label: 'AMEX' },
]

export default function RankingSidebar() {
  const [activeTab, setActiveTab] = useState('domestic')
  const [items, setItems] = useState<RankItem[]>([])
  const [updateTime, setUpdateTime] = useState('')
  const prevPrices = useRef<Record<string, number>>({})

  usePolling(() => {
    const load = activeTab === 'domestic'
      ? getMarketRanking().then(d => d.stocks)
      : getOverseasRanking(activeTab).then(d => d.stocks)
    load.then(stocks => {
      setItems(stocks || [])
      setUpdateTime(new Date().toLocaleTimeString('ko-KR'))
    }).catch(() => {})
  }, 3000)

  const switchTab = (tab: string) => {
    setActiveTab(tab)
    setItems([])
    const load = tab === 'domestic'
      ? getMarketRanking().then(d => d.stocks)
      : getOverseasRanking(tab).then(d => d.stocks)
    load.then(stocks => {
      setItems(stocks || [])
      setUpdateTime(new Date().toLocaleTimeString('ko-KR'))
    }).catch(() => {})
  }

  const isOverseas = activeTab !== 'domestic'
  const maxVol = Math.max(...items.map(s => s.volume), 1)

  return (
    <div className="card shadow-sm border-0 sticky-sidebar">
      <div className="card-header fw-bold py-2">
        <div className="d-flex justify-content-between align-items-center mb-2">
          <span><i className="fa-solid fa-fire me-1 text-danger"></i>거래량 TOP</span>
          <span className="text-muted" style={{ fontSize: '.65rem' }}>{updateTime}</span>
        </div>
        <ul className="nav nav-tabs nav-fill rank-tabs" style={{ fontSize: '.78rem', marginBottom: -8 }}>
          {tabs.map(t => (
            <li className="nav-item" key={t.key}>
              <a className={`nav-link py-1 px-2 ${activeTab === t.key ? 'active' : ''}`}
                href="#" onClick={e => { e.preventDefault(); switchTab(t.key) }}>
                {t.icon && <i className={`fa-solid ${t.icon} me-1`}></i>}{t.label}
              </a>
            </li>
          ))}
        </ul>
      </div>
      <div className="card-body p-0" style={{ maxHeight: 'calc(100vh - 200px)', overflowY: 'auto' }}>
        {items.length === 0 ? (
          <div className="text-center text-muted py-4 small">데이터 없음</div>
        ) : items.map((s, i) => {
          const cls = chgClass(s.change_rate)
          const arrow = s.change_rate > 0 ? '\u25B2' : s.change_rate < 0 ? '\u25BC' : ''
          const barPct = Math.round((s.volume / maxVol) * 100)
          const nameStr = s.stock_name || s.name || s.stock_code
          const priceStr = isOverseas ? fmtO(s.price) : fmt(s.price)
          const volStr = isOverseas ? fmtVolUS(s.volume) : fmtVol(s.volume)
          const prevKey = `rank_${s.stock_code}${isOverseas ? '_o' : ''}`
          const flashed = prevPrices.current[prevKey] !== undefined && prevPrices.current[prevKey] !== s.price
          prevPrices.current[prevKey] = s.price
          const rankCls = i < 1 ? 'rank-1' : i < 2 ? 'rank-2' : i < 3 ? 'rank-3' : 'rank-other'

          return (
            <div key={s.stock_code + i} className={`rank-item${flashed ? ' flash' : ''}`}>
              <div className={`rank-num ${rankCls}`}>{i + 1}</div>
              <div className="rank-info">
                <div className="rank-name">{nameStr}</div>
                <div className="rank-code">{s.stock_code}</div>
                <div className={`rank-bar ${s.change_rate >= 0 ? 'rank-bar-up' : 'rank-bar-down'}`} style={{ width: `${barPct}%` }}></div>
              </div>
              <div className="rank-price">
                <div className={`rank-price-val ${cls}`}>{priceStr}</div>
                <div className={`rank-change ${cls}`}>{arrow} {signStr(s.change_rate)}{fmtF(s.change_rate)}%</div>
                <div className="rank-vol">{volStr}</div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
