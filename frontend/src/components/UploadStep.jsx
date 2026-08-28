import { useState, useRef } from 'react'
import { parseZip } from '../api.js'

function formatBytes(n) {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / 1024 / 1024).toFixed(1)} MB`
}

export default function UploadStep({ onParsed }) {
  const [file, setFile] = useState(null)
  const [dragging, setDragging] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const inputRef = useRef()

  function pickFile(f) {
    if (!f || !f.name.endsWith('.zip')) {
      setError('Please select a .zip file exported from Apache Superset.')
      return
    }
    setFile(f)
    setError(null)
  }

  function onDrop(e) {
    e.preventDefault()
    setDragging(false)
    pickFile(e.dataTransfer.files[0])
  }

  async function handleAnalyze() {
    if (!file) return
    setLoading(true)
    setError(null)
    try {
      const result = await parseZip(file)
      onParsed(file, result)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="card">
      <h2>Upload Dashboard Export</h2>
      <p className="subtitle">
        Export your dashboard from the source Superset environment
        (Dashboards → Export), then upload the ZIP here.
      </p>

      {error && <div className="error-banner">{error}</div>}

      {/* Drop zone */}
      <div
        className={`drop-zone${dragging ? ' dragging' : ''}`}
        onClick={() => inputRef.current.click()}
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
      >
        <div className="dz-icon">📦</div>
        <div className="dz-label">Drag &amp; drop your export ZIP here</div>
        <div className="dz-sub">or click to browse</div>
        <input
          ref={inputRef}
          type="file"
          accept=".zip"
          onChange={(e) => pickFile(e.target.files[0])}
        />
      </div>

      {/* Selected file */}
      {file && (
        <div className="file-selected">
          <span className="file-icon">🗜️</span>
          <span className="file-name">{file.name}</span>
          <span className="file-size">{formatBytes(file.size)}</span>
        </div>
      )}

      <div className="btn-row">
        <button
          className="btn btn-primary"
          disabled={!file || loading}
          onClick={handleAnalyze}
        >
          {loading ? <><span className="spinner" /> Analysing…</> : 'Analyse Export'}
        </button>
      </div>
    </div>
  )
}
