import { useState, useEffect, useCallback } from 'react'
import { getStrategies, runBacktest as apiBt, runAiAnalysis as apiAi } from '../../api/strategies'
import type { Strategy, BacktestResult as BtResult, AuctionAlert } from '../../types'
import StrategyTable from './StrategyTable'
import AddStrategyModal from './AddStrategyModal'
import ChartSection from './ChartSection'
import BacktestModal from './BacktestModal'
import BacktestResultComp from './BacktestResult'

export default function StrategiesPage() {
  const [strategies, setStrategies] = useState<Strategy[]>([])
  const [showAdd, setShowAdd] = useState(false)
  const [chartId, setChartId] = useState<number | null>(null)
  const [chartName, setChartName] = useState('')
  const [btId, setBtId] = useState<number | null>(null)
  const [btName, setBtName] = useState('')
  const [showBt, setShowBt] = useState(false)
  const [btResult, setBtResult] = useState<BtResult | null>(null)
  const [btLoading, setBtLoading] = useState(false)

  const load = useCallback(() => { getStrategies().then(setStrategies).catch(() => {}) }, [])
  useEffect(() => { load() }, [load])

  const openChart = (id: number, name: string) => { setChartId(id); setChartName(name) }
  const closeChart = () => { setChartId(null); setChartName('') }

  const openBacktest = (id: number, name: string) => { setBtId(id); setBtName(name); setShowBt(true) }
  const runBt = async (period: string, capital: number) => {
    if (!btId) return
    setShowBt(false); setBtLoading(true); setBtResult(null)
    try {
      const d = await apiBt(btId, period, capital)
      if (d.error) alert('백테스팅 실패: ' + d.error)
      else setBtResult(d)
    } catch (e: unknown) { alert('백테스팅 오류: ' + (e as Error).message) }
    setBtLoading(false)
  }

  const aiAnalyze = async (id: number) => {
    if (!confirm('AI 분석을 실행하시겠습니까?')) return
    try {
      const d = await apiAi(id)
      if ((d as Record<string, unknown>).error) { alert('분석 실패: ' + (d as Record<string, unknown>).error); return }
      const data = d as Record<string, unknown>
      const alertData: AuctionAlert = {
        id: null, stock_code: data.stock_code as string, stock_name: data.stock_name as string,
        suggested_action: data.action as string, suggested_price: data.price as number, suggested_qty: 0,
        ai_confidence: data.confidence as number, ai_score: data.total_score as number,
        ai_summary: data.summary as string, ai_factors: data.factors as AuctionAlert['ai_factors'],
        expires_at: new Date(Date.now() + 600000).toISOString(),
      }
      window.dispatchEvent(new CustomEvent('show-auction', { detail: alertData }))
    } catch (e: unknown) { alert('분석 오류: ' + (e as Error).message) }
  }

  return (
    <>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h4 className="fw-bold mb-0">전략 관리</h4>
        <button className="btn btn-primary" onClick={() => setShowAdd(true)}>
          <i className="fa-solid fa-plus me-1"></i>전략 추가
        </button>
      </div>

      <StrategyTable strategies={strategies} activeId={chartId} onReload={load}
        onOpenChart={openChart} onOpenBacktest={openBacktest} onAiAnalyze={aiAnalyze} />

      {chartId && <ChartSection strategyId={chartId} stockName={chartName} onClose={closeChart} />}

      {showAdd && <AddStrategyModal show={showAdd} onClose={() => setShowAdd(false)} onCreated={() => { setShowAdd(false); load() }} />}
      {showBt && <BacktestModal show={showBt} stockName={btName} onClose={() => setShowBt(false)} onRun={runBt} />}

      {btLoading && (
        <div className="card shadow-sm mt-4"><div className="card-body text-center py-4">
          <i className="fa-solid fa-spinner fa-spin me-2"></i>백테스팅 실행 중...
        </div></div>
      )}
      {btResult && <BacktestResultComp data={btResult} onClose={() => setBtResult(null)} />}
    </>
  )
}
