import { useState } from 'react'
import { api } from '../api.js'

// Ordered pipeline stages -> fraction complete, for the progress bar.
const STAGE_PROGRESS = {
  queued: 0,
  downloading: 0.3,
  converting: 0.6,
  tagging: 0.85,
  done: 1,
  error: 1,
}

const STATUS_LABELS = {
  queued: 'Queued',
  downloading: 'Downloading',
  converting: 'Converting',
  tagging: 'Tagging',
  done: 'Done',
  error: 'Error',
}

const ACTIVE = new Set(['downloading', 'converting', 'tagging'])

// Pick the best playable source: the converted 432Hz file once done,
// otherwise the Spotify 30s preview if available.
function playableSrc(track) {
  if (track.status === 'done' && track.output_path) {
    return api.audioUrl(track.output_path)
  }
  return track.preview_url || ''
}

export default function TrackRow({ track, onRetry, player }) {
  const [override, setOverride] = useState('')
  const status = track.status || 'queued'
  const progress = STAGE_PROGRESS[status] ?? 0
  const isActive = ACTIVE.has(status)

  const label = STATUS_LABELS[status] || status
  const labelClass =
    status === 'done' ? 'done' : status === 'error' ? 'error' : ''

  const src = playableSrc(track)
  const isPlaying = player && src && player.playingSrc === src

  return (
    <div className="track-row">
      <div className="track-row-main">
        <div className={`art-thumb${src ? ' playable' : ''}`}
          onClick={() => src && player.togglePlay(src)}
          title={src ? (isPlaying ? 'Pause' : 'Play preview') : ''}
        >
          {track.cover_url ? (
            <img src={track.cover_url} alt="" />
          ) : (
            <div className="art-fallback">♪</div>
          )}
          {src && (
            <div className="art-play">{isPlaying ? '❚❚' : '▶'}</div>
          )}
        </div>

        <div className="track-info">
          <div className="track-title">{track.title || 'Untitled'}</div>
          <div className="track-sub">
            {track.artist}
            {track.album ? ` · ${track.album}` : ''}
          </div>
        </div>
        <div className={`status-label ${labelClass}`}>
          {status === 'done' && <span className="checkmark">Done ✓</span>}
          {status === 'error' && <span>Error ✗</span>}
          {status !== 'done' && status !== 'error' && label}
        </div>
      </div>

      {status !== 'error' && (
        <div className="progress-track">
          <div
            className={`progress-fill${isActive ? ' indeterminate' : ''}`}
            style={{ width: `${progress * 100}%` }}
          />
        </div>
      )}

      {track.warning && status !== 'error' && (
        <div className="track-warning">
          <div>{track.warning}</div>
          <div className="retry-row">
            <input
              type="text"
              placeholder="Override YouTube search query"
              value={override}
              onChange={(e) => setOverride(e.target.value)}
            />
            <button className="small-btn" onClick={() => onRetry(override || null)}>
              Retry
            </button>
          </div>
        </div>
      )}

      {status === 'error' && (
        <div>
          <div className="track-error">
            <span>✗ {track.error || 'Conversion failed'}</span>
          </div>
          <div className="retry-row">
            <input
              type="text"
              placeholder="Optional: override YouTube search query"
              value={override}
              onChange={(e) => setOverride(e.target.value)}
            />
            <button className="small-btn" onClick={() => onRetry(override || null)}>
              Retry
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
