import { useState, useRef, useEffect } from 'react'
import { sendMessage, getSessions, deleteSession, getMessages } from '../../api/chat'

interface ChatMessage {
  role: 'user' | 'bot'
  content: string
  timestamp: Date
}

interface Session {
  id: number
  title: string
  updated_at: string
}

const WELCOME_MSG: ChatMessage = {
  role: 'bot',
  content: '안녕하세요! AI 투자 챗봇입니다.\n주식, 채권, 뉴스, 재무제표 등 무엇이든 물어보세요!',
  timestamp: new Date(),
}

export default function ChatPage() {
  const [sessions, setSessions] = useState<Session[]>([])
  const [activeSessionId, setActiveSessionId] = useState<number | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([WELCOME_MSG])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // 세션 목록 로드
  useEffect(() => {
    getSessions().then(setSessions).catch(() => {})
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // 세션 선택
  const loadSession = async (sid: number) => {
    setActiveSessionId(sid)
    try {
      const msgs = await getMessages(sid)
      setMessages([
        WELCOME_MSG,
        ...msgs.map(m => ({
          role: m.role as 'user' | 'bot',
          content: m.content,
          timestamp: new Date(m.created_at),
        })),
      ])
    } catch {
      setMessages([WELCOME_MSG])
    }
  }

  // 새 대화
  const startNewChat = () => {
    setActiveSessionId(null)
    setMessages([WELCOME_MSG])
    setInput('')
    inputRef.current?.focus()
  }

  // 세션 삭제
  const handleDeleteSession = async (sid: number, e: React.MouseEvent) => {
    e.stopPropagation()
    await deleteSession(sid)
    setSessions(prev => prev.filter(s => s.id !== sid))
    if (activeSessionId === sid) startNewChat()
  }

  const handleSend = async () => {
    const text = input.trim()
    if (!text || loading) return

    setMessages(prev => [...prev, { role: 'user', content: text, timestamp: new Date() }])
    setInput('')
    setLoading(true)

    try {
      const res = await sendMessage(text, activeSessionId ?? undefined)
      setMessages(prev => [...prev, { role: 'bot', content: res.answer, timestamp: new Date() }])

      // 새 세션이면 목록 갱신
      if (!activeSessionId) {
        setActiveSessionId(res.session_id)
        getSessions().then(setSessions).catch(() => {})
      }
    } catch (e: any) {
      setMessages(prev => [
        ...prev,
        { role: 'bot', content: `오류: ${e.message}`, timestamp: new Date() },
      ])
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const formatTime = (d: Date) =>
    d.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })

  const formatDate = (s: string) => {
    const d = new Date(s)
    return d.toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' })
  }

  return (
    <div className="d-flex" style={{ height: 'calc(100vh - 60px)' }}>
      {/* 사이드 패널 - 대화 목록 */}
      <div className="chat-sidebar" style={{
        width: 220, minWidth: 220, background: '#f0f2f5',
        borderRight: '1px solid #ddd', display: 'flex',
        flexDirection: 'column', overflow: 'hidden',
      }}>
        <div style={{ padding: '12px' }}>
          <button className="btn btn-primary btn-sm w-100" onClick={startNewChat}>
            <i className="fas fa-plus me-1"></i> 새 대화
          </button>
        </div>
        <div style={{ flex: 1, overflowY: 'auto', padding: '0 8px' }}>
          {sessions.map(s => (
            <div
              key={s.id}
              onClick={() => loadSession(s.id)}
              style={{
                padding: '8px 10px', borderRadius: 8, cursor: 'pointer', marginBottom: 4,
                background: activeSessionId === s.id ? '#d4d8ff' : 'transparent',
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                fontSize: 13,
              }}
            >
              <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1 }}>
                <div style={{ fontWeight: activeSessionId === s.id ? 600 : 400 }}>
                  {s.title}
                </div>
                <div style={{ fontSize: 11, color: '#888' }}>{formatDate(s.updated_at)}</div>
              </div>
              <button
                className="btn btn-sm p-0 ms-1"
                onClick={e => handleDeleteSession(s.id, e)}
                style={{ color: '#999', fontSize: 12, border: 'none', background: 'none' }}
                title="삭제"
              >
                <i className="fas fa-trash"></i>
              </button>
            </div>
          ))}
          {sessions.length === 0 && (
            <div style={{ color: '#999', fontSize: 12, textAlign: 'center', marginTop: 20 }}>
              대화 내역이 없습니다
            </div>
          )}
        </div>
      </div>

      {/* 채팅 영역 */}
      <div className="d-flex flex-column flex-grow-1" style={{ minWidth: 0 }}>
        <h5 className="p-3 mb-0" style={{ borderBottom: '1px solid #eee' }}>
          <i className="fas fa-robot me-2"></i>AI 투자 챗봇
        </h5>

        <div className="flex-grow-1" style={{
          overflowY: 'auto', padding: 16,
          background: '#f8f9fa',
        }}>
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`d-flex mb-3 ${msg.role === 'user' ? 'justify-content-end' : 'justify-content-start'}`}
            >
              {msg.role === 'bot' && (
                <div className="me-2" style={{ flexShrink: 0 }}>
                  <div style={{
                    width: 36, height: 36, borderRadius: '50%',
                    background: '#6c63ff', display: 'flex',
                    alignItems: 'center', justifyContent: 'center',
                    color: '#fff', fontSize: 14,
                  }}>
                    <i className="fas fa-robot"></i>
                  </div>
                </div>
              )}
              <div style={{
                maxWidth: '75%', padding: '10px 14px',
                borderRadius: msg.role === 'user' ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
                background: msg.role === 'user' ? '#6c63ff' : '#fff',
                color: msg.role === 'user' ? '#fff' : '#333',
                boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
                whiteSpace: 'pre-wrap', wordBreak: 'break-word',
                fontSize: 14, lineHeight: 1.5,
              }}>
                {msg.content}
                <div style={{
                  fontSize: 11, opacity: 0.6, marginTop: 4,
                  textAlign: msg.role === 'user' ? 'right' : 'left',
                }}>
                  {formatTime(msg.timestamp)}
                </div>
              </div>
            </div>
          ))}

          {loading && (
            <div className="d-flex justify-content-start mb-3">
              <div className="me-2">
                <div style={{
                  width: 36, height: 36, borderRadius: '50%',
                  background: '#6c63ff', display: 'flex',
                  alignItems: 'center', justifyContent: 'center',
                  color: '#fff', fontSize: 14,
                }}>
                  <i className="fas fa-robot"></i>
                </div>
              </div>
              <div style={{
                padding: '12px 18px', borderRadius: '16px 16px 16px 4px',
                background: '#fff', boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
              }}>
                <div className="typing-indicator">
                  <span></span><span></span><span></span>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        <div className="p-3" style={{ borderTop: '1px solid #eee' }}>
          <div className="d-flex gap-2">
            <input
              ref={inputRef}
              type="text"
              className="form-control"
              placeholder="메시지를 입력하세요... (예: 삼성전자 현재가, 코스피 지수)"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={loading}
              autoFocus
              style={{ borderRadius: 20, padding: '10px 16px' }}
            />
            <button
              className="btn btn-primary"
              onClick={handleSend}
              disabled={loading || !input.trim()}
              style={{
                borderRadius: '50%', width: 44, height: 44,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                flexShrink: 0,
              }}
            >
              <i className={loading ? 'fas fa-spinner fa-spin' : 'fas fa-paper-plane'}></i>
            </button>
          </div>
          <div className="text-muted text-center mt-2" style={{ fontSize: 11 }}>
            비영리 교육용 챗봇 | 주식 현재가 · 뉴스 · 재무제표 · 시장 지수 · 법령 검색
          </div>
        </div>
      </div>
    </div>
  )
}
