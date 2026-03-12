import { NavLink } from 'react-router-dom'
import type { PropsWithChildren } from 'react'

const navigation = [
  { to: '/', label: 'Overview' },
  { to: '/crm', label: 'CRM' },
  { to: '/deliberation', label: 'Deliberation' },
  { to: '/due-diligence', label: 'Due Diligence' },
]

export function AppShell({ children }: PropsWithChildren) {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <p className="eyebrow">Freedom Square</p>
          <h1>Campaign Workspace</h1>
          <p className="muted">
            React migration foundation for CRM, Deliberation, and Due Diligence.
          </p>
        </div>
        <nav className="nav-list">
          {navigation.map((item) => (
            <NavLink
              className={({ isActive }) =>
                `nav-link${isActive ? ' nav-link--active' : ''}`
              }
              key={item.to}
              to={item.to}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="content">{children}</main>
    </div>
  )
}
