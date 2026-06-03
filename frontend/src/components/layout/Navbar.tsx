import { useEffect, useState } from 'react'
import { useAuth } from '../../hooks/useAuth'
import { getMode } from '../../api/settings'

export default function Navbar() {
  const { user, logout } = useAuth()
  const [mode, setModeState] = useState('paper')

  useEffect(() => {
    getMode().then(d => setModeState(d.mode)).catch(() => {})
  }, [])

  return (
    <nav className="navbar px-3 py-2 d-flex justify-content-between">
      <span className="navbar-brand">KIS 자동매매</span>
      <div className="d-flex align-items-center gap-3">
        <span className={`mode-badge ${mode === 'real' ? 'mode-real' : 'mode-paper'}`}>
          {mode === 'real' ? '실전투자' : '모의투자'}
        </span>
        {user && (
          <div className="user-info">
            <i className="fa-solid fa-user"></i> {user.name || user.username}
            <button onClick={logout}>
              <i className="fa-solid fa-right-from-bracket"></i> 로그아웃
            </button>
          </div>
        )}
      </div>
    </nav>
  )
}
