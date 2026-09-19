import { useState } from 'react'
import { api } from '../api.js'

// Inline editor for a library track's tags. Saving retags the MP3 and renames
// it to Artist/Album/NN - Title (432Hz).mp3 to match.
const stripSuffix = (title) => (title || '').replace(/\s*\(432Hz\)\s*$/i, '')

export default function EditTrackForm({ track, onSaved, onClose }) {
  const [form, setForm] = useState({
    title: stripSuffix(track.title),
    artist: track.artist || '',
    album_artist: track.album_artist || '',
    album: track.album || '',
    year: track.year || '',
    track_number: track.track_number ? String(track.track_number) : '',
    genre: track.genre || '',
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value })

  const save = async () => {
    setSaving(true)
    setError('')
    try {
      await api.editTrack({
        path: track.output_path,
        ...form,
        track_number: parseInt(form.track_number, 10) || 0,
      })
      onSaved()
    } catch (e) {
      setError(e.message || 'Save failed')
      setSaving(false)
    }
  }

  const onKeyDown = (e) => {
    if (e.key === 'Enter') save()
    if (e.key === 'Escape') onClose()
  }

  const field = (key, label, extra = {}) => (
    <label className={`edit-field${extra.wide ? ' wide' : ''}`}>
      <span>{label}</span>
      <input
        type="text"
        value={form[key]}
        onChange={set(key)}
        onKeyDown={onKeyDown}
        inputMode={extra.numeric ? 'numeric' : undefined}
      />
    </label>
  )

  return (
    <div className="edit-form">
      <div className="edit-grid">
        {field('title', 'Title', { wide: true })}
        {field('artist', 'Artist')}
        {field('album_artist', 'Album artist')}
        {field('album', 'Album', { wide: true })}
        {field('track_number', 'Track #', { numeric: true })}
        {field('year', 'Year', { numeric: true })}
        {field('genre', 'Genre', { wide: true })}
      </div>
      <div className="edit-hint">
        The file is renamed to match: Artist / Album / {form.track_number ? 'NN - ' : ''}Title (432Hz).mp3
      </div>
      {error && <div className="track-error">✗ {error}</div>}
      <div className="retry-row">
        <button className="small-btn" onClick={save} disabled={saving}>
          {saving ? 'Saving…' : 'Save'}
        </button>
        <button className="small-btn ghost" onClick={onClose} disabled={saving}>
          Cancel
        </button>
      </div>
    </div>
  )
}
