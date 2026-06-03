import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { apiMe } from '../../api/auth'
import { base64urlToBuffer, bufferToBase64url } from '../../utils/webauthn'

export default function RegisterFingerprintPage() {
  const [step, setStep] = useState<'register' | 'done'>('register')
  const [status, setStatus] = useState('')
  const [loading, setLoading] = useState(false)
  const [supported, setSupported] = useState(true)
  const [username, setUsername] = useState('')

  useEffect(() => {
    if (!window.PublicKeyCredential) setSupported(false)
    apiMe().then(d => { if (d.authenticated) setUsername(d.user.username) }).catch(() => {})
  }, [])

  const startRegistration = async () => {
    setLoading(true)
    setStatus('기기에서 지문을 인식해주세요...')
    try {
      const optRes = await fetch('/api/webauthn/register/options', { method: 'POST', credentials: 'include' })
      if (!optRes.ok) throw new Error((await optRes.json()).msg || '옵션 생성 실패')
      const options = await optRes.json()
      options.challenge = base64urlToBuffer(options.challenge)
      options.user.id = base64urlToBuffer(options.user.id)
      if (options.excludeCredentials) {
        options.excludeCredentials = options.excludeCredentials.map((c: { id: string }) => ({ ...c, id: base64urlToBuffer(c.id) }))
      }
      const credential = await navigator.credentials.create({ publicKey: options }) as PublicKeyCredential
      const attestationResponse = credential.response as AuthenticatorAttestationResponse
      const verifyRes = await fetch('/api/webauthn/register/verify', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
        body: JSON.stringify({
          id: credential.id, rawId: bufferToBase64url(credential.rawId), type: credential.type,
          response: {
            attestationObject: bufferToBase64url(attestationResponse.attestationObject),
            clientDataJSON: bufferToBase64url(attestationResponse.clientDataJSON),
          },
        }),
      })
      const result = await verifyRes.json()
      if (result.success) {
        localStorage.setItem('kis_webauthn_user', username)
        setStep('done')
      } else throw new Error(result.msg || '등록 실패')
    } catch (e: unknown) {
      const err = e as Error
      setStatus(err.name === 'NotAllowedError' ? '지문 인식이 취소되었습니다. 다시 시도해주세요.' : err.message)
      setLoading(false)
    }
  }

  return (
    <div className="fp-bg">
      <div className="fp-card">
        {step === 'register' ? (
          <>
            <i className={`fa-solid fa-fingerprint fingerprint-icon ${loading ? 'pulse' : ''}`}></i>
            <h4 className="fw-bold mb-2">지문 등록</h4>
            <p className="text-muted mb-4">지문을 등록하면 비밀번호 없이<br />빠르게 로그인할 수 있습니다.</p>
            {status && <div className="mb-3 small text-muted">{status}</div>}
            {!supported ? (
              <div className="mb-3">
                <div className="alert alert-warning small mb-2">현재 브라우저에서는 지문 등록이 지원되지 않습니다.<br /><b>Chrome 브라우저</b>에서 다시 접속하여 등록해주세요.</div>
                <Link to="/" className="btn btn-register">홈으로 이동</Link>
              </div>
            ) : (
              <>
                <button className="btn btn-register mb-3" onClick={startRegistration} disabled={loading}>
                  <i className="fa-solid fa-fingerprint me-2"></i>지문 등록하기
                </button>
                <br /><Link to="/" className="small" style={{ color: '#999', textDecoration: 'none' }}>나중에 하기</Link>
              </>
            )}
          </>
        ) : (
          <>
            <i className="fa-solid fa-circle-check fingerprint-icon success"></i>
            <h4 className="fw-bold mb-2">등록 완료!</h4>
            <p className="text-muted mb-4">지문이 성공적으로 등록되었습니다.<br />다음 로그인부터 지문인식을 사용할 수 있습니다.</p>
            <Link to="/" className="btn btn-register">시작하기</Link>
          </>
        )}
      </div>
    </div>
  )
}
