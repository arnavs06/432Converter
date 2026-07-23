// Thin fetch wrapper around the backend REST API (proxied via Vite to :8000).

async function req(method, path, body) {
  const opts = { method, headers: {} }
  if (body !== undefined) {
    opts.headers['Content-Type'] = 'application/json'
    opts.body = JSON.stringify(body)
  }
  const res = await fetch(`/api${path}`, opts)
  if (!res.ok) {
    let detail = res.statusText
    try {
      const j = await res.json()
      detail = j.detail || detail
    } catch (e) {
      /* ignore */
    }
    throw new Error(detail)
  }
  if (res.status === 204) return null
  return res.json()
}

export const api = {
  getConfig: () => req('GET', '/config'),
  saveConfig: (values) => req('POST', '/config', values),
  convert: (url) => req('POST', '/convert', { url }),
  getJobs: () => req('GET', '/jobs'),
  getStatus: (jobId) => req('GET', `/status/${jobId}`),
  retry: (jobId, idx, queryOverride) =>
    req('POST', `/retry/${jobId}/${idx}`, { query_override: queryOverride || null }),
  getStats: () => req('GET', '/stats'),
  getLibrary: () => req('GET', '/library'),
  reveal: (path) => req('POST', '/reveal', { path }),
  audioUrl: (path) => `/api/audio?path=${encodeURIComponent(path)}`,
  coverUrl: (path) => `/api/cover?path=${encodeURIComponent(path)}`,
}

// Open a WebSocket to the backend for live progress events.
export function openSocket(onMessage) {
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
  const ws = new WebSocket(`${proto}://${window.location.host}/ws`)
  ws.onmessage = (evt) => {
    try {
      onMessage(JSON.parse(evt.data))
    } catch (e) {
      /* ignore */
    }
  }
  return ws
}
