import { useState, useEffect, useCallback } from 'react'
import { useSSE } from '../../hooks/useSSE'
import { getPendingAlerts, decideAuction } from '../../api/auction'
import type { AuctionAlert } from '../../types'
import GaugeCircle from './GaugeCircle'
import FactorBars from './FactorBars'

export default function AuctionOverlay() {
  const [alert, setAlert] = useState<AuctionAlert | null>(null)
  const [show, setShow] = useState(false)

  // 주문 설정 모달 상태
  const [showOrder, setShowOrder] = useState(false)
  const [orderDecision, setOrderDecision] = useState<string>('')
  const [orderType, setOrderType] = useState<'limit' | 'market'>('limit')
  const [orderPrice, setOrderPrice] = useState(0)
  const [orderQty, setOrderQty] = useState(1)

  const showAlert = useCallback((data: AuctionAlert) => {
    setAlert(data)
    setShow(true)
  }, [])

  useSSE('/api/auction/stream', (data) => showAlert(data as AuctionAlert))

  useEffect(() => {
    getPendingAlerts().then(list => { if (list.length > 0) showAlert(list[0]) }).catch(() => {})
    const handler = (e: Event) => showAlert((e as CustomEvent).detail)
    window.addEventListener('show-auction', handler)
    return () => window.removeEventListener('show-auction', handler)
  }, [showAlert])

  const openOrderModal = (decision: string) => {
    setOrderDecision(decision)
    setOrderPrice(alert?.suggested_price || 0)
    setOrderQty(alert?.suggested_qty || 1)
    setOrderType('limit')
    setShow(false)
    setShowOrder(true)
  }

  const closeOrderModal = () => {
    setShowOrder(false)
    setShow(true)
  }

  const confirmOrder = async () => {
    if (!alert?.id) return
    const price = orderType === 'market' ? 0 : orderPrice
    const label = orderDecision === 'buy' ? '매수' : '매도'
    const priceText = orderType === 'market' ? '시장가' : `${price.toLocaleString()}원`
    if (!window.confirm(`${label} 주문을 실행합니다.\n\n${priceText} × ${orderQty}주\n\n진행하시겠습니까?`)) return

    try {
      const d = await decideAuction(alert.id, orderDecision, price, orderQty)
      setShowOrder(false)
      setAlert(null)
      if (d.message) window.alert(d.message)
    } catch { window.alert('주문 처리 실패') }
  }

  const decide = async (decision: string) => {
    if (!alert?.id) { setShow(false); return }
    if (decision === 'pass') {
      setShow(false)
      decideAuction(alert.id, 'pass').catch(() => {})
      return
    }
    openOrderModal(decision)
  }

  // 주문 설정 모달
  if (showOrder && alert) {
    const total = orderType === 'market' ? '-' : (orderPrice * orderQty).toLocaleString()
    const isBuy = orderDecision === 'buy'
    return (
      <div style={{ display: 'flex', position: 'fixed', inset: 0, background: 'rgba(0,0,0,.7)', zIndex: 10000, alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ background: '#fff', borderRadius: 16, padding: 28, minWidth: 380, maxWidth: 440, boxShadow: '0 8px 32px rgba(0,0,0,.3)' }}>
          <h5 className="fw-bold mb-3" style={{ color: isBuy ? '#0d6efd' : '#dc3545' }}>
            <i className={`fa-solid fa-arrow-${isBuy ? 'up' : 'down'} me-2`}></i>
            {isBuy ? '매수' : '매도'} 주문
          </h5>
          <div className="mb-3 p-2 rounded text-center" style={{ background: '#f8f9fa' }}>
            <span className="fw-bold">{alert.stock_name} ({alert.stock_code})</span>
          </div>
          <div className="row g-3 mb-3">
            <div className="col-12">
              <label className="form-label small fw-bold">주문 유형</label>
              <select className="form-select" value={orderType} onChange={e => {
                const v = e.target.value as 'limit' | 'market'
                setOrderType(v)
                if (v === 'market') setOrderPrice(0)
                else setOrderPrice(alert.suggested_price || 0)
              }}>
                <option value="limit">지정가</option>
                <option value="market">시장가</option>
              </select>
            </div>
            <div className="col-6">
              <label className="form-label small fw-bold">가격 (원)</label>
              <input type="number" className="form-control" value={orderPrice} min={0} step={100}
                disabled={orderType === 'market'}
                onChange={e => setOrderPrice(Number(e.target.value))} />
            </div>
            <div className="col-6">
              <label className="form-label small fw-bold">수량 (주)</label>
              <input type="number" className="form-control" value={orderQty} min={1}
                onChange={e => setOrderQty(Number(e.target.value))} />
            </div>
          </div>
          <div className="mb-4 p-3 rounded text-center" style={{ background: '#f0f4ff', border: '1px solid #d0d9f0' }}>
            <span className="text-muted">예상 주문 금액</span><br />
            <span className="fw-bold fs-4">{total}</span><span className="text-muted">원</span>
          </div>
          <div className="d-flex gap-2">
            <button className={`btn ${isBuy ? 'btn-primary' : 'btn-danger'} flex-fill py-2 fw-bold`} onClick={confirmOrder}>
              <i className="fa-solid fa-check me-1"></i>주문 실행
            </button>
            <button className="btn btn-outline-secondary flex-fill py-2" onClick={closeOrderModal}>
              취소
            </button>
          </div>
        </div>
      </div>
    )
  }

  if (!show || !alert) return null

  const posCount = (alert.ai_factors || []).filter(f => f.score > 5).length
  const negCount = (alert.ai_factors || []).filter(f => f.score < -5).length
  const verdictBg = alert.suggested_action === 'buy' ? '#fff5f5' : alert.suggested_action === 'sell' ? '#f0f5ff' : '#f8f9fa'

  return (
    <div id="auction-overlay" className="show" style={{ display: 'flex', position: 'fixed', inset: 0, background: 'rgba(0,0,0,.65)', zIndex: 9999, alignItems: 'center', justifyContent: 'center' }}>
      <div className="auction-card">
        <h5 className="fw-bold mb-3"><i className="fa-solid fa-brain text-warning me-2"></i>AI 동시호가 분석</h5>

        <div className="d-flex justify-content-between align-items-center mb-3 pb-2" style={{ borderBottom: '1px solid #eee' }}>
          <div>
            <span className="fw-bold fs-5">{alert.stock_name || '-'}</span>
            <span className="text-muted ms-1">({alert.stock_code})</span>
          </div>
          <div className="text-end">
            <span className="fw-bold fs-5">{Number(alert.suggested_price).toLocaleString()}</span><span className="text-muted">원</span>
            <span className="ms-1 small">{alert.suggested_qty}주</span>
          </div>
        </div>

        <div className="d-flex align-items-center gap-4 mb-3 p-3 rounded" style={{ background: verdictBg }}>
          <GaugeCircle score={alert.ai_score || 0} />
          <div className="flex-grow-1">
            <div className="mb-2">
              <span className={`badge fs-6 px-3 py-2 ${alert.suggested_action === 'buy' ? 'bg-primary' : alert.suggested_action === 'sell' ? 'bg-danger' : 'bg-secondary'}`}>
                {alert.suggested_action === 'buy' ? 'AI 매수 추천' : alert.suggested_action === 'sell' ? 'AI 매도 추천' : 'AI 관망 추천'}
              </span>
            </div>
            <div className="d-flex align-items-center gap-2 mb-1">
              <span style={{ fontSize: 12, fontWeight: 600, width: 40 }}>신뢰도</span>
              <div style={{ flex: 1, height: 10, background: '#e9ecef', borderRadius: 5, overflow: 'hidden' }}>
                <div style={{
                  height: '100%', width: `${alert.ai_confidence}%`, borderRadius: 5, transition: 'width 1s ease',
                  background: alert.ai_confidence >= 70 ? '#27ae60' : alert.ai_confidence >= 40 ? '#f39c12' : '#e74c3c',
                }}></div>
              </div>
              <span style={{ fontSize: 12, fontWeight: 700, width: 35, textAlign: 'right' }}>{alert.ai_confidence}%</span>
            </div>
            <div style={{ fontSize: 11, color: '#888', marginTop: 4 }}>긍정 {posCount}개 / 부정 {negCount}개 신호 감지</div>
          </div>
        </div>

        <div className="mb-3"><FactorBars factors={alert.ai_factors || []} /></div>

        <div className="p-3 rounded mb-3" style={{ background: '#f0f4ff', fontSize: '.82rem', whiteSpace: 'pre-line', lineHeight: 1.6 }}>
          {alert.ai_summary || '분석 데이터 없음'}
        </div>

        <p className="text-muted small mb-3 text-center">만료: {alert.expires_at.replace('T', ' ').slice(0, 19)}</p>

        <div className="d-flex gap-2">
          <button className="btn btn-danger flex-fill py-2" onClick={() => decide('sell')}>
            <i className="fa-solid fa-arrow-down me-1"></i>매도
          </button>
          <button className="btn btn-primary flex-fill py-2" onClick={() => decide('buy')}>
            <i className="fa-solid fa-arrow-up me-1"></i>매수
          </button>
          <button className="btn btn-secondary flex-fill py-2" onClick={() => decide('pass')}>
            <i className="fa-solid fa-hand me-1"></i>패스
          </button>
        </div>
      </div>
    </div>
  )
}
