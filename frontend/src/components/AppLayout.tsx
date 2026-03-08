import { useState } from 'react'
import type { FormEvent } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { loadActorIdentity, saveActorIdentity } from '../authHeaders'

const ALLOWED_ROLES = ['platform_admin', 'ops_coordinator', 'case_worker', 'read_only_auditor']
const FLOW_STEPS = [
  'Dashboard',
  'People',
  'Tasks',
  'Outreach',
  'Map',
  'Events',
  'Due Diligence',
  'Data',
  'Admin',
  'Deliberation',
]

export function AppLayout() {
  const initial = loadActorIdentity()
  const [actorId, setActorId] = useState(initial.actorId)
  const [actorRole, setActorRole] = useState(initial.actorRole)
  const [saved, setSaved] = useState(false)

  function onSave(e: FormEvent) {
    e.preventDefault()
    saveActorIdentity({ actorId, actorRole })
    setSaved(true)
    setTimeout(() => setSaved(false), 1000)
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <h1>CRM Rewrite Frontend</h1>
          <p className="subtitle">Diagram-style UI mode</p>
        </div>
        <form className="identity-form" onSubmit={onSave}>
          <input
            value={actorId}
            onChange={(e) => setActorId(e.target.value)}
            placeholder="x-actor-id"
            required
          />
          <select value={actorRole} onChange={(e) => setActorRole(e.target.value)}>
            {ALLOWED_ROLES.map((role) => (
              <option key={role} value={role}>
                {role}
              </option>
            ))}
          </select>
          <button type="submit">Save identity</button>
          {saved ? <span className="saved-pill">saved</span> : null}
        </form>
      </header>
      <section className="flow-strip" aria-label="Main flow map">
        {FLOW_STEPS.map((step) => (
          <div key={step} className="flow-node">
            {step}
          </div>
        ))}
      </section>
      <nav className="nav">
        <NavLink to="/app/dashboard">Dashboard</NavLink>
        <NavLink to="/app/people">People</NavLink>
        <NavLink to="/app/tasks">Tasks</NavLink>
        <NavLink to="/app/outreach">Outreach</NavLink>
        <NavLink to="/app/map">Map</NavLink>
        <NavLink to="/app/events">Events</NavLink>
        <NavLink to="/app/due-diligence">Due Diligence</NavLink>
        <NavLink to="/app/data">Data</NavLink>
        <NavLink to="/app/admin">Admin</NavLink>
        <NavLink to="/app/deliberation">Deliberation</NavLink>
        <NavLink to="/public/event-registration">Public registration</NavLink>
      </nav>
      <main className="content">
        <Outlet />
      </main>
    </div>
  )
}

