import { useState, useCallback } from 'react'
import { usePolling } from '../../hooks/usePolling'
import { getMarketPrices, getBalance } from '../../api/dashboard'
import { getExtraCodes, saveExtraCodes } from '../../utils/localStorage'
import type { IndexData, StockPrice, BalanceItem } from '../../types'
import { fmt, fmtF, chgClass, signStr } from '../../utils/format'
import IndexCard from './IndexCard'
import StockTable from './StockTable'
import OverseasSection from './OverseasSection'
import RankingSidebar from './RankingSidebar'

export default function DashboardPage() {
  const [kospi, setKospi] = useState<IndexData | null>(null)
  const [kosdaq, setKosdaq] = useState<IndexData | null>(null)
  const [stocks, setStocks] = useState<StockPrice[]>([])
  const [balance, setBalance] = useState<BalanceItem[]>([])
  const [extraCodes, setExtraCodes] = useState(getExtraCodes())
  const [updateTime, setUpdateTime] = useState('')
  const [addCode, setAddCode] = useState('')

  const loadPrices = useCallback(() => {
    const extra = getExtraCodes().join(',')
    getMarketPrices(extra).then(d => {
      setKospi(d.indices.kospi)
      setKosdaq(d.indices.kosdaq)
      setStocks(d.stocks)
      setUpdateTime(new Date().toLocaleTimeString('ko-KR'))
    }).catch(() => setUpdateTime('연결 실패'))
  }, [])

  const loadBalance = useCallback(() => {
    getBalance().then(d => setBalance(d.balance || [])).catch(() => {})
  }, [])

  usePolling(loadPrices, 3000)
  usePolling(loadBalance, 30000)

  const handleAddStock = (e: React.FormEvent) => {
    e.preventDefault()
    const code = addCode.trim()
    if (!code || code.length < 4) return
    const arr = getExtraCodes()
    if (!arr.includes(code)) {
      arr.push(code)
      saveExtraCodes(arr)
      setExtraCodes(arr)
      loadPrices()
    }
    setAddCode('')
  }

  const handleRemoveExtra = (code: string) => {
    const arr = getExtraCodes().filter(c => c !== code)
    saveExtraCodes(arr)
    setExtraCodes(arr)
    loadPrices()
  }

  return (
    <>
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h4 className="fw-bold mb-0">실시간 시세</h4>
        <div>
          <span className="text-muted small me-2">{updateTime && `업데이트: ${updateTime}`}</span>
          <span className="badge bg-success" style={{ fontSize: '.65rem' }}>LIVE 3s</span>
        </div>
      </div>

      <div className="row">
        <div className="col-lg-8">
          {/* 코스피 / 코스닥 */}
          <div className="row g-3 mb-4">
            <div className="col-md-6"><IndexCard title="KOSPI 코스피" prefix="kospi" data={kospi} /></div>
            <div className="col-md-6"><IndexCard title="KOSDAQ 코스닥" prefix="kosdaq" data={kosdaq} /></div>
          </div>

          {/* 종목 추가 */}
          <div className="card shadow-sm border-0 mb-4">
            <div className="card-body py-2">
              <form className="d-flex align-items-center gap-2" onSubmit={handleAddStock}>
                <i className="fa-solid fa-magnifying-glass text-muted"></i>
                <input type="text" className="form-control form-control-sm border-0" placeholder="종목코드 입력 (예: 005930)"
                  maxLength={6} style={{ maxWidth: 200 }} value={addCode} onChange={e => setAddCode(e.target.value)} />
                <button className="btn btn-sm btn-outline-primary" type="submit">추가</button>
              </form>
            </div>
          </div>

          <StockTable stocks={stocks} extraCodes={extraCodes} onRemoveExtra={handleRemoveExtra} />

          <OverseasSection />

          {/* 국내 보유 종목 */}
          <div className="card shadow-sm border-0 mt-4">
            <div className="card-header fw-bold">
              <i className="fa-solid fa-wallet me-2"></i>국내 보유 종목
              <button className="btn btn-sm btn-outline-secondary float-end" onClick={loadBalance}><i className="fa-solid fa-rotate-right"></i></button>
            </div>
            <div className="card-body p-0">
              <div className="table-responsive">
              <table className="table table-hover align-middle mb-0" style={{ fontSize: '.88rem' }}>
                <thead className="table-light">
                  <tr><th>종목코드</th><th>종목명</th><th className="text-end">수량</th><th className="text-end">평균단가</th><th className="text-end">현재가</th><th className="text-end">평가금액</th><th className="text-end">평가손익</th><th className="text-end">수익률</th></tr>
                </thead>
                <tbody>
                  {balance.length === 0 ? (
                    <tr><td colSpan={8} className="text-center text-muted py-4">보유 종목 없음</td></tr>
                  ) : balance.map(row => {
                    const pnl = row.eval_profit_loss || 0
                    const cls = chgClass(pnl)
                    const arrow = pnl > 0 ? 'arrow-up' : pnl < 0 ? 'arrow-down' : ''
                    const rowBg = pnl > 0 ? 'row-up' : pnl < 0 ? 'row-down' : ''
                    const evalAmt = row.current_price * row.quantity
                    return (
                      <tr key={row.stock_code} className={rowBg}>
                        <td><code>{row.stock_code}</code></td>
                        <td>{row.stock_name}</td>
                        <td className="text-end">{row.quantity}주</td>
                        <td className="text-end">{fmt(row.avg_price)}</td>
                        <td className="text-end">{fmt(row.current_price)}</td>
                        <td className={`text-end fw-bold ${cls}`}>{fmt(evalAmt)}원</td>
                        <td className={`text-end ${cls} ${arrow}`}>{signStr(pnl)}{fmt(pnl)}원</td>
                        <td className={`text-end ${cls}`}>{signStr(row.profit_loss_rate)}{fmtF(row.profit_loss_rate)}%</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
              </div>
            </div>
          </div>
        </div>

        <div className="col-lg-4">
          <RankingSidebar />
        </div>
      </div>
    </>
  )
}
