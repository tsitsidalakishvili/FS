import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { ApiError, createTask, listTasks, patchTaskStatus } from '../api'
import type { Task } from '../types'

const STATUS_OPTIONS = ['Open', 'In Progress', 'Done', 'Cancelled']

export function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [statusFilter, setStatusFilter] = useState('')
  const [ownerFilter, setOwnerFilter] = useState('')
  const [personId, setPersonId] = useState('')
  const [title, setTitle] = useState('')
  const [ownerId, setOwnerId] = useState('')
  const [description, setDescription] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function loadTasks() {
    setLoading(true)
    setError('')
    try {
      const rows = await listTasks({
        status: statusFilter || undefined,
        ownerId: ownerFilter || undefined,
        limit: 250,
      })
      setTasks(rows)
    } catch (err) {
      const detail = err instanceof ApiError ? err.message : 'Task load failed'
      setError(detail)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadTasks()
    // initial load only
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function onCreateTask(e: FormEvent) {
    e.preventDefault()
    setError('')
    try {
      await createTask({
        personId,
        title,
        ownerId,
        description: description || undefined,
      })
      setTitle('')
      setDescription('')
      await loadTasks()
    } catch (err) {
      const detail = err instanceof ApiError ? err.message : 'Task create failed'
      setError(detail)
    }
  }

  async function onUpdateStatus(taskId: string, nextStatus: string) {
    setError('')
    try {
      await patchTaskStatus(taskId, nextStatus)
      await loadTasks()
    } catch (err) {
      const detail = err instanceof ApiError ? err.message : 'Task update failed'
      setError(detail)
    }
  }

  return (
    <section>
      <h2>Tasks</h2>
      <div className="toolbar">
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="">All statuses</option>
          {STATUS_OPTIONS.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
        <input
          value={ownerFilter}
          onChange={(e) => setOwnerFilter(e.target.value)}
          placeholder="Filter ownerId"
        />
        <button onClick={() => void loadTasks()} disabled={loading}>
          {loading ? 'Loading...' : 'Refresh'}
        </button>
      </div>

      <form onSubmit={onCreateTask} className="stack">
        <h3>Create task</h3>
        <label>
          Person ID
          <input value={personId} onChange={(e) => setPersonId(e.target.value)} required />
        </label>
        <label>
          Title
          <input value={title} onChange={(e) => setTitle(e.target.value)} required />
        </label>
        <label>
          Owner ID
          <input value={ownerId} onChange={(e) => setOwnerId(e.target.value)} required />
        </label>
        <label>
          Description
          <textarea value={description} onChange={(e) => setDescription(e.target.value)} />
        </label>
        <button type="submit">Create task</button>
      </form>

      {error ? <p className="error">{error}</p> : null}

      <table>
        <thead>
          <tr>
            <th>Title</th>
            <th>Person ID</th>
            <th>Owner</th>
            <th>Status</th>
            <th>Updated</th>
          </tr>
        </thead>
        <tbody>
          {tasks.map((task) => (
            <tr key={task.taskId}>
              <td>{task.title}</td>
              <td>{task.personId}</td>
              <td>{task.ownerId}</td>
              <td>
                <select
                  value={task.status}
                  onChange={(e) => void onUpdateStatus(task.taskId, e.target.value)}
                >
                  {STATUS_OPTIONS.map((item) => (
                    <option key={item} value={item}>
                      {item}
                    </option>
                  ))}
                </select>
              </td>
              <td>{new Date(task.updatedAt).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {tasks.length === 0 ? <p>No tasks found.</p> : null}
    </section>
  )
}

