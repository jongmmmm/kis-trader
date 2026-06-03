interface Props { score: number }

export default function GaugeCircle({ score }: Props) {
  const scoreAbs = Math.min(Math.abs(score), 100)
  const circumference = 327
  const offset = circumference - (circumference * scoreAbs / 100)
  const color = score > 15 ? '#e74c3c' : score < -15 ? '#3498db' : '#f39c12'

  return (
    <div style={{ position: 'relative', width: 110, height: 110, flexShrink: 0 }}>
      <svg viewBox="0 0 120 120" width="110" height="110">
        <circle cx="60" cy="60" r="52" fill="none" stroke="#e9ecef" strokeWidth="10" />
        <circle cx="60" cy="60" r="52" fill="none" strokeWidth="10" strokeLinecap="round"
          stroke={color} strokeDasharray="327" strokeDashoffset={offset}
          transform="rotate(-90 60 60)" style={{ transition: 'stroke-dashoffset 1s ease, stroke 0.5s' }} />
      </svg>
      <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
        <span style={{ fontSize: 22, fontWeight: 800, lineHeight: 1, color }}>{score > 0 ? '+' : ''}{score.toFixed(1)}</span>
        <span style={{ fontSize: 10, color: '#999' }}>종합점수</span>
      </div>
    </div>
  )
}
