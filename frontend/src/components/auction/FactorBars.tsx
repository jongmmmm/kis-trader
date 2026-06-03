import { useState } from 'react'
import type { AiFactor } from '../../types'

interface Props { factors: AiFactor[] }

export default function FactorBars({ factors }: Props) {
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null)
  const maxScore = Math.max(...factors.map(f => Math.abs(f.score)), 30)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      {factors.map((f, i) => {
        const pct = Math.min(Math.abs(f.score) / maxScore * 100, 100)
        const isPositive = f.score > 0
        const barColor = f.score > 10 ? '#e74c3c' : f.score < -10 ? '#3498db' : '#adb5bd'
        return (
          <div key={i} onMouseEnter={() => setHoveredIdx(i)} onMouseLeave={() => setHoveredIdx(null)}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <div style={{ width: 70, fontSize: 11, fontWeight: 700, textAlign: 'right', flexShrink: 0, color: '#444' }}>{f.name}</div>
              <div style={{ flex: 1, height: 20, background: '#f1f3f5', borderRadius: 10, overflow: 'hidden', position: 'relative' }}>
                <div style={{ position: 'absolute', left: '50%', top: 0, bottom: 0, width: 1, background: '#ccc', zIndex: 1 }}></div>
                {isPositive ? (
                  <div style={{ position: 'absolute', left: '50%', top: 2, bottom: 2, width: `${pct / 2}%`, background: barColor, borderRadius: '0 8px 8px 0', transition: 'width 0.8s ease' }}></div>
                ) : (
                  <div style={{ position: 'absolute', right: '50%', top: 2, bottom: 2, width: `${pct / 2}%`, background: barColor, borderRadius: '8px 0 0 8px', transition: 'width 0.8s ease' }}></div>
                )}
              </div>
              <div style={{ width: 40, fontSize: 11, fontWeight: 700, color: barColor, textAlign: 'right' }}>
                {f.score > 0 ? '+' : ''}{f.score}
              </div>
            </div>
            {hoveredIdx === i && f.reason && (
              <div style={{ fontSize: 10, color: '#888', paddingLeft: 78, marginTop: -2 }}>{f.reason}</div>
            )}
          </div>
        )
      })}
    </div>
  )
}
