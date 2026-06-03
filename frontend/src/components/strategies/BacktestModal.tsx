import { useState, useRef, useEffect } from 'react'
import { Modal } from 'bootstrap'

interface Props {
  show: boolean
  stockName: string
  onClose: () => void
  onRun: (period: string, capital: number) => void
}

export default function BacktestModal({ show, stockName, onClose, onRun }: Props) {
  const [period, setPeriod] = useState('year')
  const [capital, setCapital] = useState('10000000')
  const modalRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (show && modalRef.current) {
      Modal.getOrCreateInstance(modalRef.current).show()
    }
  }, [show])

  const handleRun = () => {
    const cleanCapital = parseInt(capital.replace(/,/g, '').trim()) || 10000000
    if (modalRef.current) Modal.getInstance(modalRef.current)?.hide()
    onRun(period, cleanCapital)
  }

  return (
    <div className="modal fade" ref={modalRef} tabIndex={-1}>
      <div className="modal-dialog">
        <div className="modal-content">
          <div className="modal-header">
            <h5 className="modal-title"><i className="fa-solid fa-flask me-2"></i>백테스팅 설정</h5>
            <button type="button" className="btn-close" data-bs-dismiss="modal" onClick={onClose}></button>
          </div>
          <div className="modal-body">
            <div className="mb-3">
              <label className="form-label fw-bold">종목</label>
              <div className="form-control-plaintext fw-bold text-primary">{stockName}</div>
            </div>
            <div className="mb-3">
              <label className="form-label">테스트 기간</label>
              <select className="form-select" value={period} onChange={e => setPeriod(e.target.value)}>
                <option value="3month">3개월</option><option value="6month">6개월</option>
                <option value="year">1년</option><option value="3year">3년</option><option value="5year">5년</option>
              </select>
            </div>
            <div className="mb-3">
              <label className="form-label">초기 자본금 (원)</label>
              <input type="number" className="form-control" value={capital} onChange={e => setCapital(e.target.value)} />
            </div>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" data-bs-dismiss="modal" onClick={onClose}>취소</button>
            <button type="button" className="btn btn-warning" onClick={handleRun}><i className="fa-solid fa-play me-1"></i>백테스팅 실행</button>
          </div>
        </div>
      </div>
    </div>
  )
}
