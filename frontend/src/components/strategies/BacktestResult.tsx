import { useEffect, useRef } from 'react'
import { createChart, ColorType, type IChartApi } from 'lightweight-charts'
import type { BacktestResult as BtResult } from '../../types'

const PERIOD_LABELS: Record<string, string> = { '3month': '3개월', '6month': '6개월', year: '1년', '3year': '3년', '5year': '5년' }

interface Props { data: BtResult; onClose: () => void }

export default function BacktestResult({ data, onClose }: Props) {
  const chartRef = useRef<HTMLDivElement>(null)
  const chartInstance = useRef<IChartApi | null>(null)

  const totalReturn = data.total_return ?? 0
  const buyHoldReturn = data.buy_hold_return ?? 0
  const winRate = data.win_rate ?? 0
  const totalTrades = data.total_trades ?? 0
  const maxDrawdown = data.max_drawdown ?? 0
  const finalEquity = data.final_equity ?? 0
  const equityCurve = data.equity_curve ?? []
  const buyHoldCurve = data.buy_hold_curve ?? []
  const trades = data.trades ?? []

  useEffect(() => {
    if (!chartRef.current || !equityCurve.length) return
    chartRef.current.innerHTML = ''
    const chart = createChart(chartRef.current, {
      width: chartRef.current.clientWidth, height: 300,
      layout: { background: { type: ColorType.Solid, color: '#fff' }, textColor: '#333', fontSize: 11 },
      grid: { vertLines: { color: '#f0f0f0' }, horzLines: { color: '#f0f0f0' } },
      rightPriceScale: { borderColor: '#ddd' },
      timeScale: { borderColor: '#ddd', timeVisible: false },
    })
    chartInstance.current = chart

    const eq = chart.addLineSeries({ color: '#e74c3c', lineWidth: 2, title: '전략' })
    eq.setData(equityCurve.map(p => ({ time: p.time, value: p.value })))
    if (buyHoldCurve.length) {
      const bh = chart.addLineSeries({ color: '#95a5a6', lineWidth: 1, lineStyle: 2, title: '단순보유' })
      bh.setData(buyHoldCurve.map(p => ({ time: p.time, value: p.value })))
    }

    if (trades.length) {
      const markers = trades.map(t => ({
        time: t.time, position: (t.type === 'buy' ? 'belowBar' : 'aboveBar') as 'belowBar' | 'aboveBar',
        color: t.type === 'buy' ? '#e74c3c' : '#3498db',
        shape: (t.type === 'buy' ? 'arrowUp' : 'arrowDown') as 'arrowUp' | 'arrowDown',
        text: t.type === 'buy' ? 'B' : 'S',
      })).sort((a, b) => a.time < b.time ? -1 : 1)
      eq.setMarkers(markers)
    }
    chart.timeScale().fitContent()

    const el = chartRef.current
    const ro = new ResizeObserver(() => { if (chart) chart.applyOptions({ width: el.clientWidth }) })
    ro.observe(el)

    return () => { chart.remove(); ro.disconnect() }
  }, [data, equityCurve, buyHoldCurve, trades])

  const periodLabel = PERIOD_LABELS[data.period] || data.period || ''

  return (
    <div className="card shadow-sm mt-4">
      <div className="card-header">
        <div className="d-flex justify-content-between align-items-center">
          <h5 className="mb-0"><i className="fa-solid fa-flask me-2"></i>{data.stock_name || ''} {data.strategy_type?.toUpperCase() || ''} 백테스팅 ({periodLabel})</h5>
          <button className="btn btn-sm btn-outline-danger" onClick={onClose}><i className="fa-solid fa-xmark"></i></button>
        </div>
      </div>
      <div className="card-body">
        <div className="row g-3 mb-4">
          {[
            { label: '총 수익률', value: `${totalReturn > 0 ? '+' : ''}${totalReturn.toFixed(1)}%`, color: totalReturn >= 0 ? '#e74c3c' : '#3498db' },
            { label: '단순보유 수익률', value: `${buyHoldReturn > 0 ? '+' : ''}${buyHoldReturn.toFixed(1)}%`, color: buyHoldReturn >= 0 ? '#e74c3c' : '#3498db' },
            { label: '승률', value: `${winRate.toFixed(0)}%`, color: winRate >= 50 ? '#27ae60' : '#e67e22' },
            { label: '총 거래 횟수', value: `${totalTrades}회`, color: undefined },
            { label: '최대 낙폭', value: `-${maxDrawdown.toFixed(1)}%`, color: '#e74c3c' },
            { label: '최종 자산', value: `${finalEquity.toLocaleString()}원`, color: undefined },
          ].map((s, i) => (
            <div key={i} className="col-6 col-md-2">
              <div className="card border text-center h-100">
                <div className="card-body py-2 px-1">
                  <div className="text-muted small">{s.label}</div>
                  <div className={`${i === 5 ? 'fs-5' : 'fs-4'} fw-bold`} style={s.color ? { color: s.color } : {}}>{s.value}</div>
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="card border mb-3">
          <div className="card-header py-1 px-2"><small className="fw-bold">자산 곡선 (전략 vs 단순보유)</small></div>
          <div ref={chartRef} style={{ height: 300 }}></div>
        </div>

        <div className="card border">
          <div className="card-header py-1 px-2"><small className="fw-bold">거래 내역</small></div>
          <div className="card-body p-0" style={{ maxHeight: 300, overflowY: 'auto' }}>
            <table className="table table-sm table-hover mb-0">
              <thead className="table-light sticky-top">
                <tr><th>날짜</th><th>유형</th><th>가격</th><th>수량</th><th>사유</th><th>손익</th></tr>
              </thead>
              <tbody>
                {trades.length === 0 ? (
                  <tr><td colSpan={6} className="text-center text-muted py-3">거래 내역 없음</td></tr>
                ) : trades.map((t, i) => {
                  const pnl = t.pnl ?? 0
                  return (
                    <tr key={i}>
                      <td>{t.time}</td>
                      <td><span className={`badge ${t.type === 'buy' ? 'bg-danger' : 'bg-primary'}`}>{t.type === 'buy' ? '매수' : '매도'}</span></td>
                      <td>{typeof t.price === 'number' && t.price > 1000 ? t.price.toLocaleString() : t.price}</td>
                      <td>{t.qty}</td>
                      <td><small>{t.reason || ''}</small></td>
                      <td style={{ color: pnl >= 0 ? '#e74c3c' : '#3498db', fontWeight: 'bold' }}>
                        {t.pnl !== undefined ? `${pnl >= 0 ? '+' : ''}${pnl.toLocaleString()}` : '-'}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}
