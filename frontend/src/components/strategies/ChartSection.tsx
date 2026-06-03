import { useEffect, useRef, useState, useCallback } from 'react'
import { createChart, CrosshairMode, ColorType, type IChartApi } from 'lightweight-charts'
import { getChartData, getEvents } from '../../api/strategies'
import type { ChartData, ChartEvent } from '../../types'

const PERIOD_LABELS: Record<string, string> = {
  day: '일봉 (최근 30일)', month: '일봉 (최근 3개월)', year: '일봉 (최근 1년)',
  '5year': '주봉 (최근 5년)', '10year': '월봉 (최근 10년)',
}
const PERIODS = [
  { key: 'day', label: '1일' }, { key: 'month', label: '1개월' }, { key: 'year', label: '1년' },
  { key: '5year', label: '5년' }, { key: '10year', label: '10년' },
]

const COLORS = {
  maShort: '#e74c3c', maLong: '#3498db', ma60: '#9b59b6',
  volUp: 'rgba(231,76,60,0.5)', volDown: 'rgba(52,152,219,0.5)',
  rsi: '#8e44ad', macd: '#2980b9', macdSignal: '#e67e22',
  macdHistUp: 'rgba(231,76,60,0.6)', macdHistDown: 'rgba(52,152,219,0.6)',
}

interface Props { strategyId: number; stockName: string; onClose: () => void }

export default function ChartSection({ strategyId, stockName, onClose }: Props) {
  const [period, setPeriod] = useState('month')
  const [loading, setLoading] = useState(false)
  const candleRef = useRef<HTMLDivElement>(null)
  const volumeRef = useRef<HTMLDivElement>(null)
  const rsiRef = useRef<HTMLDivElement>(null)
  const macdRef = useRef<HTMLDivElement>(null)
  const tooltipRef = useRef<HTMLDivElement>(null)
  const chartsRef = useRef<IChartApi[]>([])
  const timerRef = useRef<ReturnType<typeof setInterval>>(null!)

  const destroyCharts = useCallback(() => {
    chartsRef.current.forEach(c => c.remove())
    chartsRef.current = []
  }, [])

  const mkChart = (container: HTMLElement, height: number) => {
    container.innerHTML = ''
    return createChart(container, {
      width: container.clientWidth, height,
      layout: { background: { type: ColorType.Solid, color: '#fff' }, textColor: '#333', fontSize: 11 },
      grid: { vertLines: { color: '#f0f0f0' }, horzLines: { color: '#f0f0f0' } },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: '#ddd' },
      timeScale: { borderColor: '#ddd', timeVisible: false },
    })
  }

  const renderCharts = useCallback((data: ChartData) => {
    destroyCharts()
    const candles = data.candles
    if (!candles?.length) return

    // 1. Candlestick
    const cc = mkChart(candleRef.current!, 400)
    const cs = cc.addCandlestickSeries({ upColor: '#e74c3c', downColor: '#3498db', borderUpColor: '#e74c3c', borderDownColor: '#3498db', wickUpColor: '#e74c3c', wickDownColor: '#3498db' })
    cs.setData(candles.map(c => ({ time: c.time, open: c.open, high: c.high, low: c.low, close: c.close })))
    const maS = cc.addLineSeries({ color: COLORS.maShort, lineWidth: 1, title: 'MA' + (data.params.short_period || 5) })
    maS.setData(candles.filter(c => c.ma_short > 0).map(c => ({ time: c.time, value: c.ma_short })))
    const maL = cc.addLineSeries({ color: COLORS.maLong, lineWidth: 1, title: 'MA' + (data.params.long_period || 20) })
    maL.setData(candles.filter(c => c.ma_long > 0).map(c => ({ time: c.time, value: c.ma_long })))
    const ma60 = cc.addLineSeries({ color: COLORS.ma60, lineWidth: 1, title: 'MA60' })
    ma60.setData(candles.filter(c => c.ma60 > 0).map(c => ({ time: c.time, value: c.ma60 })))
    cc.timeScale().fitContent()

    // Events
    getEvents(strategyId, period).then(evtData => {
      if (!evtData.events?.length) return
      const candleDates = candles.map(c => c.time).sort()
      // 이벤트 날짜를 가장 가까운 캔들 날짜로 스냅
      const snapToCandle = (eventDate: string): string => {
        let best = candleDates[0]
        for (const cd of candleDates) {
          if (cd <= eventDate) best = cd
          else break
        }
        return best
      }
      const evtMap: Record<string, ChartEvent> = {}
      const markers = evtData.events.map(e => {
        const snapped = snapToCandle(e.time)
        evtMap[snapped] = e
        return {
          time: snapped, position: (e.direction === 'up' ? 'aboveBar' : 'belowBar') as 'aboveBar' | 'belowBar',
          color: e.direction === 'up' ? '#e74c3c' : '#3498db',
          shape: (e.direction === 'up' ? 'arrowUp' : 'arrowDown') as 'arrowUp' | 'arrowDown',
          text: `${e.direction === 'up' ? '\u25B2' : '\u25BC'}${Math.abs(e.change_pct).toFixed(1)}%`,
        }
      }).filter(m => candleDates.includes(m.time))
        .sort((a, b) => a.time < b.time ? -1 : 1)
      // 중복 시간 제거 (같은 캔들에 여러 이벤트 매칭 시 마지막만)
      const seen = new Set<string>()
      const uniqueMarkers = markers.filter(m => { if (seen.has(m.time)) return false; seen.add(m.time); return true })
      cs.setMarkers(uniqueMarkers)

      // Tooltip
      cc.subscribeCrosshairMove(param => {
        if (!param.time || !tooltipRef.current) { if (tooltipRef.current) tooltipRef.current.style.display = 'none'; return }
        let timeKey: string
        if (typeof param.time === 'object' && 'year' in param.time) {
          timeKey = `${param.time.year}-${String(param.time.month).padStart(2, '0')}-${String(param.time.day).padStart(2, '0')}`
        } else { timeKey = String(param.time) }
        const evt = evtMap[timeKey]
        if (!evt) { tooltipRef.current.style.display = 'none'; return }
        const color = evt.direction === 'up' ? '#e74c3c' : '#3498db'
        const arrow = evt.change_pct > 0 ? '\u25B2' : '\u25BC'
        const newsHtml = evt.news?.length
          ? `<div style="margin-top:6px;border-top:1px solid #eee;padding-top:6px"><div style="font-size:11px;color:#666;margin-bottom:4px;font-weight:bold">관련 뉴스</div>${evt.news.map((n, i) => `<div style="font-size:12px;line-height:1.5;margin-bottom:3px;padding-left:8px;border-left:2px solid ${color}">${i + 1}. ${n}</div>`).join('')}</div>`
          : `<div style="font-size:12px;color:#555">${evt.reason}</div>`
        tooltipRef.current.innerHTML = `<div style="font-weight:bold;margin-bottom:6px;color:${color};font-size:14px">${evt.time} ${arrow} ${evt.change_pct > 0 ? '+' : ''}${evt.change_pct}%</div>${newsHtml}`
        const rect = candleRef.current!.getBoundingClientRect()
        const point = param.point!
        let left = rect.left + point.x + 20, top = rect.top + point.y - 10
        if (left + 390 > window.innerWidth) left = rect.left + point.x - 400
        if (top + 250 > window.innerHeight) top = window.innerHeight - 260
        tooltipRef.current.style.left = `${Math.max(10, left)}px`
        tooltipRef.current.style.top = `${Math.max(10, top)}px`
        tooltipRef.current.style.display = 'block'
      })
    }).catch(() => {})

    // 2. Volume
    const vc = mkChart(volumeRef.current!, 120)
    const vs = vc.addHistogramSeries({ priceFormat: { type: 'volume' }, priceScaleId: 'vol' })
    vs.setData(candles.map(c => ({ time: c.time, value: c.volume, color: c.close >= c.open ? COLORS.volUp : COLORS.volDown })))
    const vmaSeries = vc.addLineSeries({ color: '#f39c12', lineWidth: 1, title: 'Vol MA20', priceScaleId: 'vol' })
    vmaSeries.setData(candles.filter(c => c.vol_ma20 > 0).map(c => ({ time: c.time, value: c.vol_ma20 })))
    vc.timeScale().fitContent()

    // 3. RSI
    const rc = mkChart(rsiRef.current!, 150)
    rc.addLineSeries({ color: COLORS.rsi, lineWidth: 2, title: 'RSI' }).setData(candles.filter(c => c.rsi > 0).map(c => ({ time: c.time, value: c.rsi })))
    const rsiOver = data.params.rsi_overbought || 70
    const rsiUnder = data.params.rsi_oversold || 30
    rc.addLineSeries({ color: '#e74c3c', lineWidth: 1, lineStyle: 2, title: '과매수 ' + rsiOver }).setData(candles.map(c => ({ time: c.time, value: rsiOver })))
    rc.addLineSeries({ color: '#3498db', lineWidth: 1, lineStyle: 2, title: '과매도 ' + rsiUnder }).setData(candles.map(c => ({ time: c.time, value: rsiUnder })))
    rc.timeScale().fitContent()

    // 4. MACD
    const mc = mkChart(macdRef.current!, 150)
    mc.addLineSeries({ color: COLORS.macd, lineWidth: 2, title: 'MACD' }).setData(candles.map(c => ({ time: c.time, value: c.macd })))
    mc.addLineSeries({ color: COLORS.macdSignal, lineWidth: 1, title: 'Signal' }).setData(candles.map(c => ({ time: c.time, value: c.macd_signal })))
    mc.addHistogramSeries({ title: 'Histogram' }).setData(candles.map(c => ({ time: c.time, value: c.macd_hist, color: c.macd_hist >= 0 ? COLORS.macdHistUp : COLORS.macdHistDown })))
    mc.timeScale().fitContent()

    // Sync
    const charts = [cc, vc, rc, mc]
    chartsRef.current = charts
    let syncing = false
    charts.forEach(chart => {
      chart.timeScale().subscribeVisibleLogicalRangeChange(range => {
        if (syncing || !range) return
        syncing = true
        charts.forEach(other => { if (other !== chart) other.timeScale().setVisibleLogicalRange(range) })
        syncing = false
      })
    })

    // Resize
    const ro = new ResizeObserver(() => {
      const refs = [candleRef, volumeRef, rsiRef, macdRef]
      charts.forEach((c, i) => { if (refs[i].current) c.applyOptions({ width: refs[i].current!.clientWidth }) })
    })
    if (candleRef.current) ro.observe(candleRef.current)
  }, [strategyId, period, destroyCharts])

  const loadChart = useCallback(() => {
    setLoading(true)
    getChartData(strategyId, period).then(data => {
      setLoading(false)
      if (data.error) { alert(data.error); return }
      renderCharts(data)
    }).catch(err => { setLoading(false); alert('차트 로딩 실패: ' + err.message) })
  }, [strategyId, period, renderCharts])

  useEffect(() => {
    loadChart()
    timerRef.current = setInterval(() => {
      getChartData(strategyId, period).then(d => { if (!d.error) renderCharts(d) }).catch(() => {})
    }, 3000)
    return () => { clearInterval(timerRef.current); destroyCharts() }
  }, [strategyId, period, loadChart, renderCharts, destroyCharts])

  return (
    <div className="card shadow-sm mt-4">
      <div className="card-header">
        <div className="d-flex justify-content-between align-items-center mb-2">
          <h5 className="mb-0"><i className="fa-solid fa-chart-line me-2"></i>{stockName} 차트</h5>
          <div className="d-flex align-items-center gap-2">
            {loading && <span className="text-muted small"><i className="fa-solid fa-spinner fa-spin me-1"></i>로딩 중...</span>}
            <button className="btn btn-sm btn-outline-secondary" onClick={loadChart}><i className="fa-solid fa-rotate-right me-1"></i>새로고침</button>
            <button className="btn btn-sm btn-outline-danger" onClick={onClose}><i className="fa-solid fa-xmark"></i></button>
          </div>
        </div>
        <div className="btn-group" role="group">
          {PERIODS.map(p => (
            <button key={p.key} type="button" className={`btn btn-sm btn-outline-primary ${period === p.key ? 'active' : ''}`}
              onClick={() => setPeriod(p.key)}>{p.label}</button>
          ))}
        </div>
        <span className="ms-2 text-muted small">{PERIOD_LABELS[period]}</span>
      </div>
      <div className="card-body p-2">
        <div ref={candleRef} style={{ height: 400, position: 'relative' }}></div>
        <div ref={volumeRef} style={{ height: 120 }}></div>
        <div className="row mt-2">
          <div className="col-md-6">
            <div className="card border"><div className="card-header py-1 px-2"><small className="fw-bold">RSI</small></div><div ref={rsiRef} style={{ height: 150 }}></div></div>
          </div>
          <div className="col-md-6">
            <div className="card border"><div className="card-header py-1 px-2"><small className="fw-bold">MACD</small></div><div ref={macdRef} style={{ height: 150 }}></div></div>
          </div>
        </div>
      </div>
      <div ref={tooltipRef} style={{ display: 'none', position: 'fixed', zIndex: 9999, background: '#fff', border: '1px solid #bbb', borderRadius: 10, padding: '14px 18px', boxShadow: '0 8px 30px rgba(0,0,0,0.22)', maxWidth: 380, minWidth: 220, pointerEvents: 'none', fontSize: 13, lineHeight: 1.5 }}></div>
    </div>
  )
}
