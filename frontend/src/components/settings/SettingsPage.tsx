import { useState, useEffect } from 'react'
import { getMode, setMode as apiSetMode, refreshToken as apiRefreshToken } from '../../api/settings'

export default function SettingsPage() {
  const [currentMode, setCurrentMode] = useState('-')
  const [tokenMsg, setTokenMsg] = useState('')

  useEffect(() => {
    getMode().then(d => setCurrentMode(d.mode === 'real' ? '실전투자' : '모의투자')).catch(() => {})
  }, [])

  const changeMode = async (mode: string) => {
    if (mode === 'real' && !confirm('실전투자로 전환하면 실제 자금으로 거래됩니다.\n반드시 소액 테스트 후 사용하세요. 계속하시겠습니까?')) return
    const d = await apiSetMode(mode)
    setCurrentMode(mode === 'real' ? '실전투자' : '모의투자')
    alert(d.message)
    window.location.reload()
  }

  const handleRefreshToken = async () => {
    const d = await apiRefreshToken()
    setTokenMsg(d.message)
  }

  return (
    <>
      <h4 className="fw-bold mb-4">설정</h4>
      <div className="card shadow-sm mb-4">
        <div className="card-header fw-bold">투자 모드 전환</div>
        <div className="card-body">
          <p className="text-muted small mb-3">현재 모드: <strong>{currentMode}</strong></p>
          <div className="d-flex gap-2">
            <button className="btn btn-outline-secondary" onClick={() => changeMode('paper')}>모의투자로 전환</button>
            <button className="btn btn-outline-danger" onClick={() => changeMode('real')}>실전투자로 전환</button>
          </div>
        </div>
      </div>
      <div className="card shadow-sm">
        <div className="card-header fw-bold">KIS API 토큰</div>
        <div className="card-body">
          <p className="text-muted small mb-3">토큰은 24시간마다 자동 갱신됩니다. 오류 발생 시 수동 갱신하세요.</p>
          <button className="btn btn-outline-primary" onClick={handleRefreshToken}>토큰 수동 갱신</button>
          {tokenMsg && <div className="mt-2 text-success small">{tokenMsg}</div>}
        </div>
      </div>
    </>
  )
}
