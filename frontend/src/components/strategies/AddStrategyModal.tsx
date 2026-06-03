import { useState, useRef, useEffect } from 'react'
import { Modal } from 'bootstrap'
import { createStrategy } from '../../api/strategies'

const PARAM_DEFAULTS: Record<string, string> = {
  ma: '{"short_period":5,"long_period":20,"buy_qty":10,"stop_loss_pct":-3,"take_profit_pct":5}',
  rsi_macd: '{"rsi_period":14,"rsi_oversold":30,"rsi_overbought":70,"macd_fast":12,"macd_slow":26,"macd_signal":9,"buy_qty":10}',
  condition: '{"conditions":[{"indicator":"change_rate","operator":">","value":3}],"action":"buy","buy_qty":5}',
  ml: '{"buy_threshold":0.65,"sell_threshold":0.35,"buy_qty":10}',
}

interface Props { show: boolean; onClose: () => void; onCreated: () => void }

export default function AddStrategyModal({ show, onClose, onCreated }: Props) {
  const [name, setName] = useState('')
  const [exchange, setExchange] = useState('')
  const [code, setCode] = useState('')
  const [stockName, setStockName] = useState('')
  const [type, setType] = useState('ma')
  const [params, setParams] = useState(PARAM_DEFAULTS.ma)
  const [mode, setMode] = useState('paper')
  const modalRef = useRef<HTMLDivElement>(null)

  useEffect(() => { setParams(PARAM_DEFAULTS[type] || '{}') }, [type])

  useEffect(() => {
    if (show && modalRef.current) {
      Modal.getOrCreateInstance(modalRef.current).show()
    }
  }, [show])

  const handleAdd = async () => {
    let parsedParams
    try { parsedParams = JSON.parse(params) }
    catch { alert('파라미터 JSON 형식 오류'); return }
    await createStrategy({ name, stock_code: code, stock_name: stockName, exchange, strategy_type: type, params: parsedParams, mode })
    if (modalRef.current) Modal.getInstance(modalRef.current)?.hide()
    onCreated()
  }

  return (
    <div className="modal fade" ref={modalRef} tabIndex={-1}>
      <div className="modal-dialog">
        <div className="modal-content">
          <div className="modal-header">
            <h5 className="modal-title">전략 추가</h5>
            <button type="button" className="btn-close" data-bs-dismiss="modal" onClick={onClose}></button>
          </div>
          <div className="modal-body">
            <div className="mb-3">
              <label className="form-label">전략명</label>
              <input type="text" className="form-control" value={name} onChange={e => setName(e.target.value)} placeholder="삼성전자 MA전략" />
            </div>
            <div className="mb-3">
              <label className="form-label">시장</label>
              <select className="form-select" value={exchange} onChange={e => setExchange(e.target.value)}>
                <option value="">국내 (코스피/코스닥)</option>
                <option value="NAS">NASDAQ</option><option value="NYS">NYSE</option><option value="AMS">AMEX</option>
                <option value="HKS">홍콩</option><option value="SHS">상해</option><option value="SZS">심천</option>
                <option value="TSE">도쿄</option><option value="HNX">하노이</option><option value="HSX">호치민</option>
              </select>
            </div>
            <div className="mb-3">
              <label className="form-label">{exchange ? '티커' : '종목코드'}</label>
              <input type="text" className="form-control" value={code} onChange={e => setCode(e.target.value)} placeholder={exchange ? 'AAPL' : '005930'} />
            </div>
            <div className="mb-3">
              <label className="form-label">종목명</label>
              <input type="text" className="form-control" value={stockName} onChange={e => setStockName(e.target.value)} placeholder="삼성전자" />
            </div>
            <div className="mb-3">
              <label className="form-label">전략 유형</label>
              <select className="form-select" value={type} onChange={e => setType(e.target.value)}>
                <option value="ma">이동평균선 (MA/EMA)</option>
                <option value="rsi_macd">RSI / MACD</option>
                <option value="condition">조건식 직접 설정</option>
                <option value="ml">AI/ML 예측 (RandomForest)</option>
              </select>
            </div>
            <div className="mb-3">
              <label className="form-label">파라미터 (JSON)</label>
              <textarea className="form-control font-monospace" rows={5} value={params} onChange={e => setParams(e.target.value)}></textarea>
            </div>
            <div className="mb-3">
              <label className="form-label">모드</label>
              <select className="form-select" value={mode} onChange={e => setMode(e.target.value)}>
                <option value="paper">모의투자</option>
                <option value="real">실전투자</option>
              </select>
            </div>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" data-bs-dismiss="modal" onClick={onClose}>취소</button>
            <button type="button" className="btn btn-primary" onClick={handleAdd}>추가</button>
          </div>
        </div>
      </div>
    </div>
  )
}
