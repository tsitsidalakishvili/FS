import { useEffect, useMemo, useState } from 'react'
import { ApiError, listEvents, listPeople, listTasks } from '../api'
import type { Event, Person, Task } from '../types'

export function DashboardPage() {
  const [people, setPeople] = useState<Person[]>([])
  const [tasks, setTasks] = useState<Task[]>([])
  const [events, setEvents] = useState<Event[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function load() {
    setLoading(true)
    setError('')
    try {
      const [peopleRows, taskRows, eventRows] = await Promise.all([
        listPeople({ includeArchived: true, limit: 500 }),
        listTasks({ limit: 500 }),
        listEvents(500),
      ])
      setPeople(peopleRows)
      setTasks(taskRows)
      setEvents(eventRows)
    } catch (err) {
      const detail = err instanceof ApiError ? err.message : 'Failed loading dashboard data'
      setError(detail)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  const metrics = useMemo(() => {
    const activePeople = people.filter((item) => item.status !== 'ARCHIVED').length
    const archivedPeople = people.length - activePeople
    const openTasks = tasks.filter((item) => item.status !== 'Done' && item.status !== 'Cancelled').length
    const doneTasks = tasks.filter((item) => item.status === 'Done').length
    const publishedEvents = events.filter((item) => item.published).length
    return { activePeople, archivedPeople, openTasks, doneTasks, publishedEvents }
  }, [people, tasks, events])

  return (
    <section>
      <h2>Dashboard</h2>
      <div className="toolbar">
        <button onClick={() => void load()} disabled={loading}>
          {loading ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>
      {error ? <p className="error">{error}</p> : null}
      <div className="card-grid">
        <article className="metric-card">
          <h4>Active people</h4>
          <p>{metrics.activePeople}</p>
        </article>
        <article className="metric-card">
          <h4>Archived people</h4>
          <p>{metrics.archivedPeople}</p>
        </article>
        <article className="metric-card">
          <h4>Open tasks</h4>
          <p>{metrics.openTasks}</p>
        </article>
        <article className="metric-card">
          <h4>Done tasks</h4>
          <p>{metrics.doneTasks}</p>
        </article>
        <article className="metric-card">
          <h4>Published events</h4>
          <p>{metrics.publishedEvents}</p>
        </article>
      </div>

      <h3>Latest tasks</h3>
      <table>
        <thead>
          <tr>
            <th>Task</th>
            <th>Status</th>
            <th>Owner</th>
            <th>Updated</th>
          </tr>
        </thead>
        <tbody>
          {tasks.slice(0, 8).map((item) => (
            <tr key={item.taskId}>
              <td>{item.title}</td>
              <td>{item.status}</td>
              <td>{item.ownerId}</td>
              <td>{new Date(item.updatedAt).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}

