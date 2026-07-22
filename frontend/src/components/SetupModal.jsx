import { useState } from 'react'

export default function SetupModal({ onSave }) {
  const [clientId, setClientId] = useState('')
  const [clientSecret, setClientSecret] = useState('')
  const [busy, setBusy] = useState(false)

  const save = async () => {
    if (!clientId.trim() || !clientSecret.trim() || busy) return
    setBusy(true)
    try {
      await onSave({
        SPOTIFY_CLIENT_ID: clientId.trim(),
        SPOTIFY_CLIENT_SECRET: clientSecret.trim(),
      })
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="modal-overlay">
      <div className="modal">
        <h2>Welcome to 432 Converter</h2>
        <p>
          To fetch track metadata, enter your Spotify API credentials. Create a
          free app at{' '}
          <a href="https://developer.spotify.com/dashboard" target="_blank" rel="noreferrer">
            developer.spotify.com
          </a>{' '}
          and copy the Client ID and Secret.
        </p>

        <div className="field">
          <label>Spotify Client ID</label>
          <input
            type="text"
            value={clientId}
            onChange={(e) => setClientId(e.target.value)}
            autoFocus
          />
        </div>

        <div className="field">
          <label>Spotify Client Secret</label>
          <input
            type="password"
            value={clientSecret}
            onChange={(e) => setClientSecret(e.target.value)}
          />
        </div>

        <button
          className="modal-save"
          onClick={save}
          disabled={busy || !clientId.trim() || !clientSecret.trim()}
        >
          {busy ? 'Saving…' : 'Save & Continue'}
        </button>
      </div>
    </div>
  )
}
