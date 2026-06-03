import { useRef } from 'react'
import type { StockPrice } from '../../types'
import { fmt, fmtF, chgClass, signStr } from '../../utils/format'

interface Props {
  stocks: StockPrice[]
  extraCodes: string[]
  onRemoveExtra: (code: string) => void
}

export default function StockTable({ stocks, extraCodes, onRemoveExtra }: Props) {
  const prevPrices = useRef<Record<string, number>>({})

  return (
    <div className="card shadow-sm border-0">
      <div className="card-header fw-bold d-flex justify-content-between align-items-center">
        <span><i className="fa-solid fa-table-list me-2"></i>전체 종목 시세</span>
        <span className="badge bg-secondary">{stocks.length}종목</span>
      </div>
      <div className="card-body p-0">
        <div className="table-responsive">
          <table className="table table-hover align-middle mb-0" style={{ fontSize: '.88rem' }}>
            <thead className="table-light">
              <tr>
                <th style={{ width: 90 }}>종목코드</th><th>종목명</th>
                <th className="text-end">시가</th><th className="text-end">현재가</th>
                <th className="text-end">전일대비(%)</th><th className="text-end">고가</th>
                <th className="text-end">저가</th><th className="text-end">거래량</th>
                <th style={{ width: 40 }}></th>
              </tr>
            </thead>
            <tbody>
              {stocks.length === 0 ? (
                <tr><td colSpan={9} className="text-center text-muted py-4">등록된 종목이 없습니다.</td></tr>
              ) : stocks.map(s => {
                const cls = chgClass(s.change_rate)
                const arrow = s.change_rate > 0 ? 'arrow-up' : s.change_rate < 0 ? 'arrow-down' : ''
                const rowBg = s.change_rate > 0 ? 'row-up' : s.change_rate < 0 ? 'row-down' : ''
                const flashed = prevPrices.current[s.stock_code] !== undefined && prevPrices.current[s.stock_code] !== s.price
                prevPrices.current[s.stock_code] = s.price
                const isExtra = extraCodes.includes(s.stock_code)
                return (
                  <tr key={s.stock_code} className={`${flashed ? 'flash ' : ''}${rowBg}`}>
                    <td><code>{s.stock_code}</code></td>
                    <td>{s.stock_name || '-'}</td>
                    <td className="text-end fw-bold">{fmt(s.open)}</td>
                    <td className={`text-end fw-bold ${cls} ${arrow}`}>{fmt(s.price)}</td>
                    <td className={`text-end ${cls}`}>{signStr(s.change_rate)}{fmtF(s.change_rate)}%</td>
                    <td className="text-end" style={{ color: '#e74c3c' }}>{fmt(s.high)}</td>
                    <td className="text-end" style={{ color: '#3498db' }}>{fmt(s.low)}</td>
                    <td className="text-end">{fmt(s.volume)}</td>
                    <td>{isExtra && <i className="fa-solid fa-xmark remove-btn" onClick={() => onRemoveExtra(s.stock_code)}></i>}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
