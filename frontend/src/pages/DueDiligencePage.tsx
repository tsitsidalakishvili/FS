import { useState } from 'react'
import type { FormEvent } from 'react'

import {
  listSubjectInvestigations,
  searchDueDiligenceSubjects,
} from '../api/coreApi'
import { StatusBadge } from '../components/StatusBadge'
import type {
  DueDiligenceSubjectSummary,
  InvestigationRunSummary,
} from '../types/api'

export function DueDiligencePage() {
  const [query, setQuery] = useState('')
  const [subjects, setSubjects] = useState<DueDiligenceSubjectSummary[]>([])
  const [selectedSubject, setSelectedSubject] =
    useState<DueDiligenceSubjectSummary | null>(null)
  const [investigations, setInvestigations] = useState<InvestigationRunSummary[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSearch = async (event: FormEvent) => {
    event.preventDefault()
    setLoading(true)
    setError('')
    setSelectedSubject(null)
    setInvestigations([])
    try {
      const response = await searchDueDiligenceSubjects(query)
      setSubjects(response.items)
    } catch (caughtError) {
      setSubjects([])
      setError(caughtError instanceof Error ? caughtError.message : 'Search failed.')
    } finally {
      setLoading(false)
    }
  }

  const loadInvestigations = async (subject: DueDiligenceSubjectSummary) => {
    setLoading(true)
    setError('')
    setSelectedSubject(subject)
    try {
      const response = await listSubjectInvestigations(subject.subject_id)
      setInvestigations(response.items)
    } catch (caughtError) {
      setInvestigations([])
      setError(caughtError instanceof Error ? caughtError.message : 'Load failed.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page-stack">
      <section className="section-header">
        <div>
          <p className="eyebrow">Due Diligence</p>
          <h2>Subjects and investigation history</h2>
        </div>
        <p className="muted">
          First React slice backed by the new Core API and persisted DD run history.
        </p>
      </section>

      <section className="panel-card">
        <form className="form-grid" onSubmit={handleSearch}>
          <label className="field">
            <span>Search tracked subject</span>
            <input
              minLength={2}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search people or organizations..."
              value={query}
            />
          </label>
          <div className="form-actions">
            <button disabled={loading || query.trim().length < 2} type="submit">
              {loading ? 'Searching…' : 'Search subjects'}
            </button>
          </div>
        </form>
        {error ? <p className="error-text">{error}</p> : null}
      </section>

      <section className="split-layout">
        <article className="panel-card">
          <div className="table-header">
            <h3>Subjects</h3>
            <span className="muted">{subjects.length} found</span>
          </div>
          <div className="subject-list">
            {subjects.length === 0 ? (
              <p className="empty-state">Search to load Due Diligence subjects.</p>
            ) : (
              subjects.map((subject) => (
                <button
                  className={`subject-card${
                    selectedSubject?.subject_id === subject.subject_id
                      ? ' subject-card--active'
                      : ''
                  }`}
                  key={subject.subject_id}
                  onClick={() => void loadInvestigations(subject)}
                  type="button"
                >
                  <div>
                    <strong>{subject.subject_name}</strong>
                    <div className="table-subtext">{subject.subject_label}</div>
                  </div>
                  <StatusBadge tone="neutral">
                    {subject.investigation_count} runs
                  </StatusBadge>
                </button>
              ))
            )}
          </div>
        </article>

        <article className="panel-card">
          <div className="table-header">
            <h3>Investigations</h3>
            <span className="muted">
              {selectedSubject ? selectedSubject.subject_name : 'Select a subject'}
            </span>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Started</th>
                  <th>Status</th>
                  <th>Kind</th>
                  <th>Sources</th>
                  <th>Errors</th>
                </tr>
              </thead>
              <tbody>
                {investigations.length === 0 ? (
                  <tr>
                    <td className="empty-state" colSpan={5}>
                      {selectedSubject
                        ? 'No investigation history found.'
                        : 'Choose a subject to load investigation runs.'}
                    </td>
                  </tr>
                ) : (
                  investigations.map((investigation) => (
                    <tr key={investigation.run_id}>
                      <td>{investigation.started_at ?? '—'}</td>
                      <td>{investigation.status ?? '—'}</td>
                      <td>{investigation.run_kind ?? '—'}</td>
                      <td>{investigation.selected_sources.join(', ') || '—'}</td>
                      <td>{investigation.error_count}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </article>
      </section>
    </div>
  )
}
