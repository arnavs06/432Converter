import { useEffect, useRef, useState } from 'react'

export default function InputBar({ onConvert }) {
  const [url, setUrl] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const inputRef = useRef(null)

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  const submit = async () => {
    const trimmed = url.trim()
    if (!trimmed || busy) return
    setBusy(true)
    setError('')
    try {
      await onConvert(trimmed)
      setUrl('')
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  const onKeyDown = (e) => {
    if (e.key === 'Enter') submit()
  }

  return (
    <div>
      <div className="inputbar-wrap">
        <div className="inputbar">
          <input
            ref={inputRef}
            type="text"
            placeholder="Paste a Spotify, SoundCloud, or YouTube link (track, album, or playlist)"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            onKeyDown={onKeyDown}
          />
          <button className="convert-btn" onClick={submit} disabled={busy || !url.trim()}>
            {busy ? 'Working…' : 'Convert'}
          </button>
        </div>
      </div>
      {error && <div className="input-error">{error}</div>}
    </div>
  )
}
