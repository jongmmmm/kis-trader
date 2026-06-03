import { useState, useEffect, useCallback } from 'react'
import { getOrders } from '../../api/orders'
import type { Order } from '../../types'

export default function OrdersPage() {
  const [orders, setOrders] = useState<Order[]>([])
  const [mode, setMode] = useState('')
  const [trigger, setTrigger] = useState('')

  const load = useCallback(() => {
    getOrders(mode, trigger).then(setOrders).catch(() => {})
  }, [mode, trigger])

  useEffect(() => { load() }, [load])

  return (
    <>
      <h4 className="fw-bold mb-4">주문 내역</h4>
      <div className="d-flex gap-2 mb-3">
        <select className="form-select w-auto" value={mode} onChange={e => setMode(e.target.value)}>
          <option value="">전체 모드</option><option value="paper">모의</option><option value="real">실전</option>
        </select>
        <select className="form-select w-auto" value={trigger} onChange={e => setTrigger(e.target.value)}>
          <option value="">전체 유형</option><option value="auto">자동</option><option value="auction_manual">동시호가 수동</option>
        </select>
      </div>
      <div className="card shadow-sm">
        <div className="card-body p-0">
          <table className="table table-hover mb-0">
            <thead className="table-light">
              <tr><th>시간</th><th>종목</th><th>구분</th><th>가격</th><th>수량</th><th>상태</th><th>유형</th><th>모드</th></tr>
            </thead>
            <tbody>
              {orders.length === 0 ? (
                <tr><td colSpan={8} className="text-center text-muted py-4">주문 내역 없음</td></tr>
              ) : orders.map(o => (
                <tr key={o.id}>
                  <td>{o.created_at.replace('T', ' ').slice(0, 16)}</td>
                  <td>{o.stock_code}</td>
                  <td className={o.order_type === 'buy' ? 'text-danger' : 'text-primary'}>{o.order_type === 'buy' ? '매수' : '매도'}</td>
                  <td>{Number(o.price).toLocaleString()}원</td>
                  <td>{o.quantity}주</td>
                  <td>{o.status}</td>
                  <td>{o.trigger === 'auto' ? '자동' : '동시호가'}</td>
                  <td>{o.mode === 'real' ? '실전' : '모의'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  )
}
