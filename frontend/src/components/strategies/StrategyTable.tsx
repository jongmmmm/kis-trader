import type { Strategy } from '../../types'
import { toggleStrategy, deleteStrategy } from '../../api/strategies'

const TYPE_LABELS: Record<string, string> = { ma: 'MA/EMA', rsi_macd: 'RSI/MACD', condition: '조건식', ml: 'AI/ML' }
const EX_LABELS: Record<string, string> = { NAS: 'NASDAQ', NYS: 'NYSE', AMS: 'AMEX', HKS: '홍콩', SHS: '상해', SZS: '심천', TSE: '도쿄', HNX: '하노이', HSX: '호치민' }

interface Props {
  strategies: Strategy[]
  activeId: number | null
  onReload: () => void
  onOpenChart: (id: number, name: string) => void
  onOpenBacktest: (id: number, name: string) => void
  onAiAnalyze: (id: number) => void
}

export default function StrategyTable({ strategies, activeId, onReload, onOpenChart, onOpenBacktest, onAiAnalyze }: Props) {
  const handleToggle = async (id: number) => {
    await toggleStrategy(id)
    onReload()
  }

  const handleDelete = async (id: number) => {
    if (!confirm('삭제하시겠습니까?')) return
    await deleteStrategy(id)
    onReload()
  }

  return (
    <div className="card shadow-sm">
      <div className="card-body p-0">
        <div className="table-responsive">
        <table className="table table-hover mb-0">
          <thead className="table-light">
            <tr><th>이름</th><th>시장</th><th>종목</th><th>전략유형</th><th>모드</th><th>상태</th><th>관리</th></tr>
          </thead>
          <tbody>
            {strategies.length === 0 ? (
              <tr><td colSpan={7} className="text-center text-muted py-4">등록된 전략이 없습니다</td></tr>
            ) : strategies.map(s => (
              <tr key={s.id} style={{ cursor: 'pointer' }} className={activeId === s.id ? 'table-active' : ''}
                onClick={() => onOpenChart(s.id, s.stock_name || s.stock_code)}>
                <td>{s.name}</td>
                <td>{EX_LABELS[s.exchange] || '국내'}</td>
                <td>{s.stock_code} {s.stock_name}</td>
                <td>{TYPE_LABELS[s.strategy_type] || s.strategy_type}</td>
                <td>{s.mode === 'real' ? '실전' : '모의'}</td>
                <td>
                  <span className={`badge ${s.is_active ? 'bg-success' : 'bg-secondary'}`} style={{ cursor: 'pointer' }}
                    onClick={e => { e.stopPropagation(); handleToggle(s.id) }}>
                    {s.is_active ? '활성' : '비활성'}
                  </span>
                </td>
                <td className="d-flex gap-1" onClick={e => e.stopPropagation()}>
                  <button className="btn btn-sm btn-outline-warning" title="백테스팅" onClick={() => onOpenBacktest(s.id, s.stock_name || s.stock_code)}>
                    <i className="fa-solid fa-flask"></i>
                  </button>
                  <button className="btn btn-sm btn-outline-info" title="AI 분석" onClick={() => onAiAnalyze(s.id)}>
                    <i className="fa-solid fa-brain"></i>
                  </button>
                  <button className="btn btn-sm btn-outline-danger" onClick={() => handleDelete(s.id)}>삭제</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      </div>
    </div>
  )
}
