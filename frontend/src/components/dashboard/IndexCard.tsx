import type { IndexData } from '../../types'
import { fmtF, fmt, chgClass, signStr } from '../../utils/format'

interface Props {
  title: string
  prefix: string
  data: IndexData | null
}

export default function IndexCard({ title, data }: Props) {
  if (!data) {
    return (
      <div className="card shadow-sm border-0">
        <div className="card-body">
          <div className="text-muted small fw-bold">{title}</div>
          <div className="fs-2 fw-bold mt-1">연결 실패</div>
        </div>
      </div>
    )
  }

  const cls = chgClass(data.change_val)
  const arrow = data.change_val > 0 ? 'arrow-up' : data.change_val < 0 ? 'arrow-down' : ''

  return (
    <div className={`card shadow-sm border-0 idx-card-${cls} bg-${cls}`}>
      <div className="card-body">
        <div className="d-flex justify-content-between align-items-start">
          <div>
            <div className="text-muted small fw-bold">{title}</div>
            <div className={`fs-2 fw-bold mt-1 ${cls}`}>{fmtF(data.index)}</div>
          </div>
          <div className="text-end">
            <div className={`fs-5 fw-bold ${cls} ${arrow}`}>{signStr(data.change_val)}{fmtF(data.change_val)}</div>
            <div className={`small ${cls}`}>{signStr(data.change_rate)}{fmtF(data.change_rate)}%</div>
          </div>
        </div>
        <div className="d-flex gap-3 mt-2 small text-muted flex-wrap">
          <span>시가 <strong>{fmtF(data.open)}</strong></span>
          <span>고가 <strong>{fmtF(data.high)}</strong></span>
          <span>저가 <strong>{fmtF(data.low)}</strong></span>
          <span>거래량 <strong>{fmt(data.volume)}</strong></span>
        </div>
      </div>
    </div>
  )
}
