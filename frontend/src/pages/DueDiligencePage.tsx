import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'

const WATCHLIST_KEY = 'crm_due_diligence_watchlist'
const DUE_DILIGENCE_URL = import.meta.env.VITE_DUE_DILIGENCE_APP_URL || ''

type WatchItem = {
  id: string
  name: string
  kind: 'person' | 'organization'
}

function loadWatchlist(): WatchItem[] {
  try {
    const raw = localStorage.getItem(WATCHLIST_KEY)
    return raw ? (JSON.parse(raw) as WatchItem[]) : []
  } catch {
    return []
  }
}

export function DueDiligencePage() {
  const [watchlist, setWatchlist] = useState<WatchItem[]>([])
  const [name, setName] = useState('')
  const [kind, setKind] = useState<'person' | 'organization'>('person')

  useEffect(() => {
    setWatchlist(loadWatchlist())
  }, [])

  function save(next: WatchItem[]) {
    setWatchlist(next)
    localStorage.setItem(WATCHLIST_KEY, JSON.stringify(next))
  }

  function onAdd(e: FormEvent) {
    e.preventDefault()
    const trimmed = name.trim()
    if (!trimmed) return
    save([{ id: `${Date.now()}`, name: trimmed, kind }, ...watchlist])
    setName('')
  }

  function onRemove(id: string) {
    save(watchlist.filter((item) => item.id !== id))
  }

  return (
    <section>
      <h2>Due Diligence</h2>
      <p>Streamlit parity: quick watchlist + external DD app launch.</p>
      {DUE_DILIGENCE_URL ? (
        <p>
          <a href={DUE_DILIGENCE_URL} target="_blank" rel="noreferrer">
            Open Due Diligence app
          </a>
        </p>
      ) : (
        <p className="error">Set VITE_DUE_DILIGENCE_APP_URL to enable direct app launch.</p>
      )}

      <form onSubmit={onAdd} className="toolbar">
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Name to monitor" />
        <select value={kind} onChange={(e) => setKind(e.target.value as 'person' | 'organization')}>
          <option value="person">Person</option>
          <option value="organization">Organization</option>
        </select>
        <button type="submit">Add to watchlist</button>
      </form>

      <table>
        <thead>
          <tr>
            <th>Name</th>
            <th>Type</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {watchlist.map((item) => (
            <tr key={item.id}>
              <td>{item.name}</td>
              <td>{item.kind}</td>
              <td>
                <button onClick={() => onRemove(item.id)}>Remove</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {watchlist.length === 0 ? <p>No watchlist entries yet.</p> : null}
    </section>
  )
}

