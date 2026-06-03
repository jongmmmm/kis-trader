import { useState, useMemo } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { apiSignup, checkUsername } from '../../api/auth'

export default function SignupPage() {
  const navigate = useNavigate()
  const [form, setForm] = useState({
    username: '', password: '', password2: '', name: '', phone: '',
    emailLocal: '', emailDomain: 'naver.com', loginMethod: 'password',
    birthYear: '', birthMonth: '', birthDay: '',
  })
  const [idHint, setIdHint] = useState({ msg: '', ok: false })
  const [errors, setErrors] = useState<string[]>([])

  const years = useMemo(() => Array.from({ length: 61 }, (_, i) => 2010 - i), [])
  const months = useMemo(() => Array.from({ length: 12 }, (_, i) => i + 1), [])
  const days = useMemo(() => Array.from({ length: 31 }, (_, i) => i + 1), [])

  const set = (key: string, val: string) => setForm(f => ({ ...f, [key]: val }))

  const pwValid = form.password.length >= 8 && /[A-Za-z]/.test(form.password) && /\d/.test(form.password) && /[!@#$%^&*(),.?":{}|<>]/.test(form.password)
  const pw2Match = form.password2 === form.password && form.password2.length > 0

  const checkDup = async () => {
    if (form.username.length < 6) { setIdHint({ msg: '6자 이상 입력해주세요.', ok: false }); return }
    const d = await checkUsername(form.username)
    setIdHint({ msg: d.msg, ok: d.available })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const email = form.emailLocal && form.emailDomain ? `${form.emailLocal}@${form.emailDomain}` : ''
    const birthDate = form.birthYear && form.birthMonth && form.birthDay
      ? `${form.birthYear}-${form.birthMonth.padStart(2, '0')}-${form.birthDay.padStart(2, '0')}` : ''
    try {
      const d = await apiSignup({
        username: form.username, password: form.password, password2: form.password2,
        name: form.name, phone: form.phone, email, birth_date: birthDate, login_method: form.loginMethod,
      })
      if (d.success) navigate(d.redirect || '/login')
    } catch (err: unknown) {
      setErrors([(err as Error).message])
    }
  }

  return (
    <div className="signup-bg">
      <div className="signup-card">
        <h3 className="text-center mb-1">회원가입</h3>
        <p className="text-muted text-center mb-4">회원이 되어 다양한 혜택을 경험해 보세요!</p>

        {errors.length > 0 && <div className="alert alert-danger py-2 small">{errors.map((e, i) => <div key={i}>{e}</div>)}</div>}

        <form onSubmit={handleSubmit}>
          <div className="mb-3">
            <label className="form-label">아이디 <span className={`hint ${idHint.ok ? 'hint-ok' : 'hint-err'}`}>{idHint.msg}</span></label>
            <div className="d-flex gap-2">
              <input type="text" className="form-control" value={form.username} onChange={e => set('username', e.target.value)}
                placeholder="아이디 입력 (6~20자)" minLength={6} maxLength={20} required />
              <button type="button" className="btn" style={{ background: '#00bcd4', color: '#fff', fontWeight: 600, borderRadius: 8, whiteSpace: 'nowrap' }} onClick={checkDup}>중복 확인</button>
            </div>
          </div>

          <div className="mb-3">
            <label className="form-label">비밀번호
              <span className={`hint ${form.password.length === 0 ? '' : pwValid ? 'hint-ok' : 'hint-err'}`}>
                {form.password.length === 0 ? '' : pwValid ? '사용 가능한 비밀번호입니다.' : '문자, 숫자, 특수문자를 포함해야 합니다.'}
              </span>
            </label>
            <input type="password" className="form-control" value={form.password} onChange={e => set('password', e.target.value)}
              placeholder="비밀번호 입력 (문자, 숫자, 특수문자 포함 8~20자)" minLength={8} maxLength={20} required autoComplete="new-password" />
          </div>

          <div className="mb-3">
            <label className="form-label">비밀번호 확인
              <span className={`hint ${form.password2.length === 0 ? '' : pw2Match ? 'hint-ok' : 'hint-err'}`}>
                {form.password2.length === 0 ? '' : pw2Match ? '비밀번호가 일치합니다.' : '비밀번호가 일치하지 않습니다.'}
              </span>
            </label>
            <input type="password" className="form-control" value={form.password2} onChange={e => set('password2', e.target.value)}
              placeholder="비밀번호 재입력" required autoComplete="new-password" />
          </div>

          <div className="mb-3">
            <label className="form-label">이름</label>
            <input type="text" className="form-control" value={form.name} onChange={e => set('name', e.target.value)} placeholder="이름을 입력해주세요" required />
          </div>

          <div className="mb-3">
            <label className="form-label">전화번호</label>
            <input type="tel" className="form-control" value={form.phone} onChange={e => set('phone', e.target.value)} placeholder="휴대폰 번호 입력 (* 제외 11자리)" maxLength={11} />
          </div>

          <div className="mb-3">
            <label className="form-label">이메일 주소</label>
            <div className="d-flex align-items-center gap-2">
              <input type="text" className="form-control" value={form.emailLocal} onChange={e => set('emailLocal', e.target.value)} placeholder="이메일 주소" />
              <span>@</span>
              <select className="form-select" value={form.emailDomain} onChange={e => set('emailDomain', e.target.value)}>
                <option value="naver.com">naver.com</option>
                <option value="gmail.com">gmail.com</option>
                <option value="daum.net">daum.net</option>
                <option value="hanmail.net">hanmail.net</option>
                <option value="kakao.com">kakao.com</option>
              </select>
            </div>
          </div>

          <div className="mb-3">
            <label className="form-label">로그인 방식</label>
            <div className="d-flex gap-3">
              <div className="form-check">
                <input className="form-check-input" type="radio" name="loginMethod" value="password" checked={form.loginMethod === 'password'} onChange={() => set('loginMethod', 'password')} />
                <label className="form-check-label"><i className="fa-solid fa-keyboard me-1"></i>비밀번호 입력</label>
              </div>
              <div className="form-check">
                <input className="form-check-input" type="radio" name="loginMethod" value="webauthn" checked={form.loginMethod === 'webauthn'} onChange={() => set('loginMethod', 'webauthn')} />
                <label className="form-check-label"><i className="fa-solid fa-fingerprint me-1"></i>지문인식</label>
              </div>
            </div>
            {form.loginMethod === 'webauthn' && <div className="small text-muted mt-1">회원가입 후 지문 등록 화면으로 이동합니다.</div>}
          </div>

          <div className="mb-4">
            <label className="form-label">생년월일</label>
            <div className="d-flex gap-2">
              <select className="form-select" value={form.birthYear} onChange={e => set('birthYear', e.target.value)}>
                <option value="">년도</option>
                {years.map(y => <option key={y} value={y}>{y}</option>)}
              </select>
              <select className="form-select" value={form.birthMonth} onChange={e => set('birthMonth', e.target.value)}>
                <option value="">월</option>
                {months.map(m => <option key={m} value={m}>{m}</option>)}
              </select>
              <select className="form-select" value={form.birthDay} onChange={e => set('birthDay', e.target.value)}>
                <option value="">일</option>
                {days.map(d => <option key={d} value={d}>{d}</option>)}
              </select>
            </div>
          </div>

          <div className="d-flex justify-content-center gap-3">
            <button type="submit" className="btn btn-signup">가입하기</button>
            <Link to="/login" className="btn btn-cancel">가입취소</Link>
          </div>
        </form>
      </div>
    </div>
  )
}
