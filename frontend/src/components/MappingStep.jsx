import { useState } from 'react'
import { transformZip, downloadBlob } from '../api.js'

export default function MappingStep({ file, parseResult, onTransformed, onBack }) {
  // database_mappings: [{ source_name, target_name, target_sqlalchemy_uri }]
  const [dbMappings, setDbMappings] = useState(() =>
    parseResult.databases.map((db) => ({
      source_name: db.name,
      target_name: db.name,
      target_sqlalchemy_uri: '',
    }))
  )

  // schema_mappings: [{ source, target }]
  const [schemaMappings, setSchemaMappings] = useState(() =>
    parseResult.schemas.map((s) => ({ source: s, target: s }))
  )

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // ── Field update helpers ───────────────────────────────────────────────

  function setDbField(idx, field, value) {
    setDbMappings((prev) => prev.map((m, i) => i === idx ? { ...m, [field]: value } : m))
  }

  function setSchemaTarget(idx, value) {
    setSchemaMappings((prev) => prev.map((m, i) => i === idx ? { ...m, target: value } : m))
  }

  function copySourceUriToTarget(idx) {
    setDbField(idx, 'target_sqlalchemy_uri', parseResult.databases[idx]?.sqlalchemy_uri ?? '')
  }

  // ── Validation ─────────────────────────────────────────────────────────

  function validate() {
    for (const m of dbMappings) {
      if (!m.target_sqlalchemy_uri.trim()) return 'All target connection URIs are required.'
      if (!m.target_name.trim()) return 'All target database names are required.'
    }
    return null
  }

  // ── Submit ─────────────────────────────────────────────────────────────

  async function handleTransform() {
    const err = validate()
    if (err) { setError(err); return }

    setLoading(true)
    setError(null)

    const config = {
      database_mappings: dbMappings,
      schema_mappings: schemaMappings,
    }

    try {
      const { filename, blob, summary } = await transformZip(file, config)
      downloadBlob(blob, filename)
      onTransformed(summary)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  // ── Render ─────────────────────────────────────────────────────────────

  return (
    <div className="card">
      <h2>Configure Environment Mappings</h2>
      <p className="subtitle">
        The export contains <strong>{parseResult.databases.length}</strong> database connection(s),{' '}
        <strong>{parseResult.schemas.filter(Boolean).length}</strong> unique schema(s),{' '}
        <strong>{parseResult.dataset_count}</strong> datasets, and{' '}
        <strong>{parseResult.chart_count}</strong> charts across{' '}
        <strong>{parseResult.dashboard_count}</strong> dashboard(s).
      </p>

      {error && <div className="error-banner">{error}</div>}

      {/* ── Database connections ── */}
      <div className="section-title">Database Connections</div>
      <table className="mapping-table">
        <colgroup>
          <col className="col-name" />
          <col className="col-uri" />
          <col className="col-name" />
          <col className="col-uri" />
        </colgroup>
        <thead>
          <tr>
            <th>Source Name</th>
            <th>Source URI</th>
            <th>Target Name</th>
            <th>Target URI *</th>
          </tr>
        </thead>
        <tbody>
          {dbMappings.map((m, i) => (
            <tr key={m.source_name}>
              <td><span className="source-val">{m.source_name}</span></td>
              <td>
                <span className="source-val uri-val">
                  {parseResult.databases[i]?.sqlalchemy_uri ?? ''}
                </span>
              </td>
              <td>
                <input
                  className="mapping-input"
                  value={m.target_name}
                  onChange={(e) => setDbField(i, 'target_name', e.target.value)}
                  placeholder="target_db_name"
                />
              </td>
              <td>
                <div className="uri-target-cell">
                  <textarea
                    className={`mapping-input mapping-textarea${!m.target_sqlalchemy_uri.trim() ? ' invalid' : ''}`}
                    value={m.target_sqlalchemy_uri}
                    onChange={(e) => setDbField(i, 'target_sqlalchemy_uri', e.target.value)}
                    placeholder="mysql+pymysql://user:pass@qa-host:9030"
                    rows={2}
                  />
                  <button
                    type="button"
                    className="btn btn-outline btn-small"
                    onClick={() => copySourceUriToTarget(i)}
                  >
                    Use source URI
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* ── Schema mappings ── */}
      <div className="section-title">Schema Mappings</div>
      <table className="mapping-table">
        <thead>
          <tr>
            <th>Source Schema</th>
            <th>Target Schema</th>
          </tr>
        </thead>
        <tbody>
          {schemaMappings.map((m, i) => (
            <tr key={i}>
              <td>
                <span className="source-val">{m.source || <em>(empty)</em>}</span>
              </td>
              <td>
                <input
                  className="mapping-input"
                  value={m.target}
                  onChange={(e) => setSchemaTarget(i, e.target.value)}
                  placeholder={m.source ? 'e.g. qa_analytics' : '(leave empty or fill in)'}
                  disabled={!m.source}
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="btn-row">
        <button className="btn btn-outline" onClick={onBack} disabled={loading}>
          ← Back
        </button>
        <button
          className="btn btn-primary"
          onClick={handleTransform}
          disabled={loading}
        >
          {loading
            ? <><span className="spinner" /> Transforming…</>
            : 'Transform & Download'}
        </button>
      </div>
    </div>
  )
}
