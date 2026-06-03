import { useState, useRef, useCallback } from 'react'
import { usePolling } from '../../hooks/usePolling'
import { getOverseasPrices, getOverseasBalance } from '../../api/dashboard'
import { getOverseasCodes, saveOverseasCodes } from '../../utils/localStorage'
import type { OverseasStock, BalanceItem } from '../../types'
import { fmtO, fmtF, fmtVol, chgClass, signStr } from '../../utils/format'

const EXCD_LABELS: Record<string, string> = { NAS: 'NASDAQ', NYS: 'NYSE', AMS: 'AMEX', HKS: 'HK', SHS: 'SHA', SZS: 'SZA', TSE: 'TSE', HNX: 'HNX', HSX: 'HSX' }

export default function OverseasSection() {
  const [, setCodes] = useState(getOverseasCodes())
  const [stocks, setStocks] = useState<OverseasStock[]>([])
  const [balance, setBalance] = useState<BalanceItem[]>([])
  const [excd, setExcd] = useState('NAS')
  const [ticker, setTicker] = useState('')
  const [updateTime, setUpdateTime] = useState('')
  const prevPrices = useRef<Record<string, number>>({})

  const loadPrices = useCallback(() => {
    const c = getOverseasCodes()
    if (!c.length) { setStocks([]); return }
    getOverseasPrices(c.join(',')).then(d => {
      setStocks(d.stocks || [])
      setUpdateTime(new Date().toLocaleTimeString('ko-KR'))
    }).catch(() => {})
  }, [])

  const loadBal = useCallback(() => {
    getOverseasBalance().then(d => setBalance(d.balance || [])).catch(() => {})
  }, [])

  usePolling(loadPrices, 10000)
  usePolling(loadBal, 60000)

  const addStock = (e: React.FormEvent) => {
    e.preventDefault()
    const code = ticker.trim().toUpperCase()
    if (!code) return
    const key = `${code}:${excd}`
    const arr = getOverseasCodes()
    if (!arr.includes(key)) {
      arr.push(key)
      saveOverseasCodes(arr)
      setCodes(arr)
      loadPrices()
    }
    setTicker('')
  }

  const removeStock = (key: string) => {
    const arr = getOverseasCodes().filter(c => c !== key)
    saveOverseasCodes(arr)
    setCodes(arr)
    loadPrices()
  }

  return (
    <>
      <div className="d-flex justify-content-between align-items-center mt-5 mb-3">
        <h4 className="fw-bold mb-0"><i className="fa-solid fa-globe me-2"></i>해외주식 시세</h4>
        <span className="text-muted small">{updateTime && `업데이트: ${updateTime}`}</span>
      </div>

      <div className="card shadow-sm border-0 mb-4">
        <div className="card-body py-2">
          <form className="d-flex align-items-center gap-2" onSubmit={addStock}>
            <i className="fa-solid fa-earth-americas text-muted"></i>
            <select className="form-select form-select-sm border-0" style={{ maxWidth: 120 }} value={excd} onChange={e => setExcd(e.target.value)}>
              {['NAS', 'NYS', 'AMS', 'HKS', 'SHS', 'SZS', 'TSE', 'HNX', 'HSX'].map(x => (
                <option key={x} value={x}>{EXCD_LABELS[x] || x}</option>
              ))}
            </select>
            <input type="text" className="form-control form-control-sm border-0" style={{ maxWidth: 160 }}
              placeholder="티커 입력 (예: AAPL)" value={ticker} onChange={e => setTicker(e.target.value)} />
            <button className="btn btn-sm btn-outline-primary" type="submit">추가</button>
          </form>
        </div>
      </div>

      <div className="card shadow-sm border-0">
        <div className="card-header fw-bold d-flex justify-content-between align-items-center">
          <span><i className="fa-solid fa-chart-line me-2"></i>해외 종목 시세</span>
          <span className="badge bg-secondary">{stocks.length}종목</span>
        </div>
        <div className="card-body p-0">
          <div className="table-responsive">
            <table className="table table-hover align-middle mb-0" style={{ fontSize: '.88rem' }}>
              <thead className="table-light">
                <tr><th>거래소</th><th>티커</th><th>종목명</th><th className="text-end">시가</th><th className="text-end">현재가</th><th className="text-end">전일대비(%)</th><th className="text-end">고가</th><th className="text-end">저가</th><th className="text-end">거래량</th><th style={{ width: 40 }}></th></tr>
              </thead>
              <tbody>
                {stocks.length === 0 ? (
                  <tr><td colSpan={10} className="text-center text-muted py-4">해외 종목을 추가하세요</td></tr>
                ) : stocks.map(s => {
                  const cls = chgClass(s.change_rate)
                  const arrow = s.change_rate > 0 ? 'arrow-up' : s.change_rate < 0 ? 'arrow-down' : ''
                  const rowBg = s.change_rate > 0 ? 'row-up' : s.change_rate < 0 ? 'row-down' : ''
                  const key = `${s.stock_code}:${s.exchange}`
                  const flashed = prevPrices.current[key] !== undefined && prevPrices.current[key] !== s.price
                  prevPrices.current[key] = s.price
                  return (
                    <tr key={key} className={`${flashed ? 'flash ' : ''}${rowBg}`}>
                      <td><span className="badge bg-info text-dark" style={{ fontSize: '.7rem' }}>{EXCD_LABELS[s.exchange] || s.exchange}</span></td>
                      <td><code>{s.stock_code}</code></td>
                      <td>{s.name || '-'}</td>
                      <td className="text-end fw-bold">{fmtO(s.open)}</td>
                      <td className={`text-end fw-bold ${cls} ${arrow}`}>{fmtO(s.price)}</td>
                      <td className={`text-end ${cls}`}>{signStr(s.change_rate)}{fmtF(s.change_rate)}%</td>
                      <td className="text-end">{fmtO(s.high)}</td>
                      <td className="text-end">{fmtO(s.low)}</td>
                      <td className="text-end">{fmtVol(s.volume)}</td>
                      <td><i className="fa-solid fa-xmark remove-btn" onClick={() => removeStock(key)}></i></td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* 해외 보유 종목 */}
      <div className="card shadow-sm border-0 mt-4">
        <div className="card-header fw-bold">
          <i className="fa-solid fa-sack-dollar me-2"></i>해외 보유 종목
          <button className="btn btn-sm btn-outline-secondary float-end" onClick={loadBal}><i className="fa-solid fa-rotate-right"></i></button>
        </div>
        <div className="card-body p-0">
          <table className="table table-hover align-middle mb-0" style={{ fontSize: '.88rem' }}>
            <thead className="table-light">
              <tr><th>거래소</th><th>티커</th><th>종목명</th><th className="text-end">수량</th><th className="text-end">평균단가</th><th className="text-end">현재가</th><th className="text-end">평가손익</th><th className="text-end">수익률</th><th className="text-end">통화</th></tr>
            </thead>
            <tbody>
              {balance.length === 0 ? (
                <tr><td colSpan={9} className="text-center text-muted py-4">해외 보유 종목 없음</td></tr>
              ) : balance.map(row => {
                const pnl = row.eval_profit_loss || 0
                const cls = chgClass(pnl)
                const arrow = pnl > 0 ? 'arrow-up' : pnl < 0 ? 'arrow-down' : ''
                const rowBg = pnl > 0 ? 'row-up' : pnl < 0 ? 'row-down' : ''
                return (
                  <tr key={row.stock_code} className={rowBg}>
                    <td><span className="badge bg-info text-dark" style={{ fontSize: '.7rem' }}>{row.exchange || '-'}</span></td>
                    <td><code>{row.stock_code}</code></td>
                    <td>{row.stock_name}</td>
                    <td className="text-end">{row.quantity}주</td>
                    <td className="text-end">{fmtO(row.avg_price)}</td>
                    <td className="text-end">{fmtO(row.current_price)}</td>
                    <td className={`text-end ${cls} ${arrow}`}>{signStr(pnl)}{fmtO(pnl)}</td>
                    <td className={`text-end ${cls}`}>{signStr(row.profit_loss_rate)}{fmtF(row.profit_loss_rate)}%</td>
                    <td className="text-end"><span className="badge bg-secondary">{row.currency || 'USD'}</span></td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </>
  )
}
