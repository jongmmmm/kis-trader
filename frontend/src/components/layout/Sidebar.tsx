import { NavLink } from 'react-router-dom'

const links = [
  { to: '/', icon: 'fa-chart-line', label: '대시보드' },
  { to: '/strategies', icon: 'fa-robot', label: '전략 관리' },
  { to: '/orders', icon: 'fa-list', label: '주문 내역' },
  { to: '/chat', icon: 'fa-comments', label: 'AI 챗봇' },
  { to: '/esg', icon: 'fa-leaf', label: 'ESG 관리' },
  { to: '/settings', icon: 'fa-gear', label: '설정' },
]

export default function Sidebar() {
  return (
    <nav className="sidebar">
      {links.map(l => (
        <NavLink key={l.to} to={l.to} end={l.to === '/'} className={({ isActive }) => isActive ? 'active' : ''}>
          <i className={`fa-solid ${l.icon} me-2`}></i><span>{l.label}</span>
        </NavLink>
      ))}
    </nav>
  )
}
