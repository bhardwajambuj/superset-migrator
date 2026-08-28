export default function SummaryStep({ summary, onReset }) {
  return (
    <div className="card" style={{ textAlign: 'center' }}>
      <div className="success-icon">✅</div>
      <h2>Transform Complete</h2>
      <p className="subtitle" style={{ marginBottom: 0 }}>
        Your migrated ZIP has been downloaded. Import it into the target
        Superset environment via <strong>Dashboards → Import</strong>.
      </p>

      <div className="summary-grid">
        <div className="summary-stat">
          <div className="stat-value">{summary.databases_patched}</div>
          <div className="stat-label">Database connection(s) patched</div>
        </div>
        <div className="summary-stat">
          <div className="stat-value">{summary.schemas_patched}</div>
          <div className="stat-label">Schema value(s) replaced</div>
        </div>
        <div className="summary-stat">
          <div className="stat-value">{summary.datasets_patched}</div>
          <div className="stat-label">Dataset file(s) updated</div>
        </div>
        <div className="summary-stat">
          <div className="stat-value">{summary.chart_uuids_backfilled ?? 0}</div>
          <div className="stat-label">Chart UUID(s) backfilled in layout</div>
        </div>
        <div className="summary-stat">
          <div className="stat-value">{summary.files_unchanged}</div>
          <div className="stat-label">File(s) passed through unchanged</div>
        </div>
      </div>

      <div className="btn-row" style={{ justifyContent: 'center' }}>
        <button className="btn btn-primary" onClick={onReset}>
          Migrate Another Dashboard
        </button>
      </div>
    </div>
  )
}
