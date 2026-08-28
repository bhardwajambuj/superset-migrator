/**
 * api.js — Thin wrappers around the backend REST API.
 */

const BASE = '/api'

/**
 * Upload a ZIP and get back the detected databases + schemas.
 * @param {File} file
 * @returns {Promise<ParseResult>}
 */
export async function parseZip(file) {
  const form = new FormData()
  form.append('file', file)

  const res = await fetch(`${BASE}/parse`, { method: 'POST', body: form })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? 'Parse failed')
  }
  return res.json()
}

/**
 * Upload a ZIP + mapping config and trigger a file download of the transformed ZIP.
 * Also returns a summary object parsed from response headers.
 *
 * @param {File}   file
 * @param {object} config  { database_mappings, schema_mappings }
 * @returns {Promise<{ filename: string, blob: Blob, summary: object }>}
 */
export async function transformZip(file, config) {
  const form = new FormData()
  form.append('file', file)
  form.append('config', JSON.stringify(config))

  const res = await fetch(`${BASE}/transform`, { method: 'POST', body: form })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? 'Transform failed')
  }

  // Read summary from custom response headers
  const summary = {
    databases_patched: parseInt(res.headers.get('X-Databases-Patched') ?? '0'),
    schemas_patched: parseInt(res.headers.get('X-Schemas-Patched') ?? '0'),
    datasets_patched: parseInt(res.headers.get('X-Datasets-Patched') ?? '0'),
    chart_uuids_backfilled: parseInt(
      res.headers.get('X-Chart-Uuids-Backfilled') ?? '0',
    ),
    files_unchanged: parseInt(res.headers.get('X-Files-Unchanged') ?? '0'),
  }

  const blob = await res.blob()

  // Extract filename from Content-Disposition header
  const cd = res.headers.get('Content-Disposition') ?? ''
  const match = cd.match(/filename="?([^"]+)"?/)
  const filename = match ? match[1] : 'dashboard_migrated.zip'

  return { filename, blob, summary }
}

/**
 * Trigger a browser download of a Blob.
 */
export function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}
