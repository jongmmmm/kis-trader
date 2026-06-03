import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import { base64urlToBuffer, bufferToBase64url } from '../../utils/webauthn'

export default function LoginPage() {
  const { login, user } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [remember, setRemember] = useState(true)
  const [error, setError] = useState('')
  const [savedUser, setSavedUser] = useState('')
  const [hasWebauthn, setHasWebauthn] = useState(false)
  const [webauthnStatus, setWebauthnStatus] = useState('')

  useEffect(() => {
    if (user) navigate('/', { replace: true })
  }, [user, navigate])

  useEffect(() => {
    try {
      const stored = localStorage.getItem('kis_credentials')
      if (stored) {
        const cred = JSON.parse(stored)
        setSavedUser(cred.u)
      }
    } catch {}
    const wUser = localStorage.getItem('kis_webauthn_user')
    if (wUser && window.PublicKeyCredential) setHasWebauthn(true)
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (remember) {
      localStorage.setItem('kis_credentials', JSON.stringify({ u: username, p: btoa(password) }))
    }
    const res = await login(username, password, remember)
    if (res.success) navigate('/')
    else setError(res.msg || '로그인 실패')
  }

  const autoLogin = async () => {
    try {
      const stored = localStorage.getItem('kis_credentials')
      if (!stored) { setError('저장된 로그인 정보가 없습니다.'); return }
      const cred = JSON.parse(stored)
      const res = await login(cred.u, atob(cred.p), true)
      if (res.success) navigate('/')
      else setError(res.msg || '자동 로그인 실패')
    } catch { setError('저장된 정보가 손상되었습니다.') }
  }

  const webauthnLogin = async () => {
    const wUsername = localStorage.getItem('kis_webauthn_user')
    if (!wUsername) { setWebauthnStatus('등록된 지문 계정이 없습니다.'); return }
    setWebauthnStatus('기기에서 지문을 인식해주세요...')
    try {
      const optRes = await fetch('/api/webauthn/login/options', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: wUsername }), credentials: 'include',
      })
      if (!optRes.ok) throw new Error((await optRes.json()).msg || '옵션 생성 실패')
      const options = await optRes.json()
      options.challenge = base64urlToBuffer(options.challenge)
      if (options.allowCredentials) {
        options.allowCredentials = options.allowCredentials.map((c: { id: string }) => ({
          ...c, id: base64urlToBuffer(c.id),
        }))
      }
      const assertion = await navigator.credentials.get({ publicKey: options }) as PublicKeyCredential
      const assertionResponse = assertion.response as AuthenticatorAssertionResponse
      const verifyRes = await fetch('/api/webauthn/login/verify', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
        body: JSON.stringify({
          id: assertion.id, rawId: bufferToBase64url(assertion.rawId), type: assertion.type,
          response: {
            authenticatorData: bufferToBase64url(assertionResponse.authenticatorData),
            clientDataJSON: bufferToBase64url(assertionResponse.clientDataJSON),
            signature: bufferToBase64url(assertionResponse.signature),
            userHandle: assertionResponse.userHandle ? bufferToBase64url(assertionResponse.userHandle) : null,
          },
        }),
      })
      const result = await verifyRes.json()
      if (result.success) window.location.href = '/'
      else throw new Error(result.msg || '인증 실패')
    } catch (e: unknown) {
      const err = e as Error
      setWebauthnStatus(err.name === 'NotAllowedError' ? '지문 인식이 취소되었습니다.' : err.message)
    }
  }

  return (
    <div className="login-bg">
      <div className="login-card">
        <h3 className="fw-bold text-center mb-1">KIS 자동매매</h3>
        <p className="text-muted text-center mb-4">계정에 로그인하세요</p>

        {error && <div className="alert alert-danger py-2 small">{error}</div>}

        {hasWebauthn && (
          <div className="mb-3">
            <button className="btn quick-btn btn-biometric w-100" onClick={webauthnLogin}>
              <i className="fa-solid fa-fingerprint me-2"></i>지문인식 로그인
            </button>
            {webauthnStatus && <div className="text-center small mt-2 text-muted">{webauthnStatus}</div>}
            <div className="divider"><span>또는 직접 입력</span></div>
          </div>
        )}

        {savedUser && !hasWebauthn && (
          <div className="mb-3">
            <p className="text-center small text-muted mb-2">{savedUser} 계정으로 빠른 로그인</p>
            <button className="btn quick-btn btn-autologin w-100" onClick={autoLogin}>
              <i className="fa-solid fa-bolt me-2"></i>자동 로그인
            </button>
            <div className="divider"><span>또는 직접 입력</span></div>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="mb-3">
            <label className="form-label small fw-bold">아이디</label>
            <input type="text" className="form-control" value={username} onChange={e => setUsername(e.target.value)}
              placeholder="아이디 입력" required autoComplete="username" />
          </div>
          <div className="mb-3">
            <label className="form-label small fw-bold">비밀번호</label>
            <input type="password" className="form-control" value={password} onChange={e => setPassword(e.target.value)}
              placeholder="비밀번호 입력" required autoComplete="current-password" />
          </div>
          <div className="form-check mb-3">
            <input className="form-check-input" type="checkbox" checked={remember} onChange={e => setRemember(e.target.checked)} id="remember" />
            <label className="form-check-label small" htmlFor="remember">다음에 자동 로그인 / 지문인식 사용</label>
          </div>
          <button type="submit" className="btn btn-login text-white w-100 py-2 mb-3">
            <i className="fa-solid fa-right-to-bracket me-1"></i>로그인
          </button>
        </form>
        <div className="text-center">
          <Link to="/signup" className="text-decoration-none small">계정이 없으신가요? <strong>회원가입</strong></Link>
        </div>
      </div>
    </div>
  )
}
