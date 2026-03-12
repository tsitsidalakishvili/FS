import { Link } from 'react-router-dom'

export function HomePage() {
  return (
    <div className="page-stack">
      <section className="hero-card">
        <p className="eyebrow">Migration in progress</p>
        <h2>New web platform foundation</h2>
        <p className="hero-copy">
          This React app is the new frontend shell for Freedom Square. It already
          connects to the Deliberation API and a new Core API for CRM and Due Diligence.
        </p>
      </section>

      <section className="card-grid">
        <article className="panel-card">
          <h3>CRM</h3>
          <p>
            Search people from Neo4j through the new Core API. This is the first
            API-first replacement for server-side Streamlit profile search.
          </p>
          <Link className="inline-link" to="/crm">
            Open CRM search
          </Link>
        </article>

        <article className="panel-card">
          <h3>Deliberation</h3>
          <p>
            Uses the existing deployed Deliberation backend. You can list and
            create conversations from the React UI today.
          </p>
          <Link className="inline-link" to="/deliberation">
            Open Deliberation
          </Link>
        </article>

        <article className="panel-card">
          <h3>Due Diligence</h3>
          <p>
            Search tracked subjects and inspect persisted investigation history
            from the new Core API.
          </p>
          <Link className="inline-link" to="/due-diligence">
            Open Due Diligence
          </Link>
        </article>
      </section>
    </div>
  )
}
