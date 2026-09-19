import { useState } from 'react'
import { api } from '../api.js'
import EditTrackForm from './EditTrackForm.jsx'

// Library view built from the actual files on disk (via /api/library), so
// every converted track shows up regardless of job history.
export default function Completed({ albums, player, onChanged }) {
  const [editing, setEditing] = useState(null) // output_path being edited

  if (!albums || albums.length === 0) return null

  const totalTracks = albums.reduce((n, a) => n + a.tracks.length, 0)

  const reveal = async (path) => {
    if (!path) return
    try {
      await api.reveal(path)
    } catch (e) {
      /* ignore */
    }
  }

  return (
    <div>
      <div className="section-title">
        Library · {totalTracks} {totalTracks === 1 ? 'track' : 'tracks'}
      </div>
      {albums.map((group, gi) => (
        <div className="album-group" key={gi}>
          <div className="album-head">
            {group.cover_path ? (
              <img className="album-head-art" src={api.coverUrl(group.cover_path)} alt="" />
            ) : (
              <div className="album-head-art art-fallback">♪</div>
            )}
            <div className="album-head-meta">
              <div className="album-head-title">{group.album || 'Unknown Album'}</div>
              <div className="album-head-sub">
                {group.artist}
                {group.year ? ` · ${group.year}` : ''} · {group.tracks.length}{' '}
                {group.tracks.length === 1 ? 'track' : 'tracks'}
              </div>
            </div>
          </div>

          {group.tracks.map((t, i) => {
            const src = t.output_path ? api.audioUrl(t.output_path) : ''
            const isPlaying = player && src && player.playingSrc === src
            const isEditing = editing && editing === t.output_path
            return (
              <div key={t.output_path || i}>
                <div className="completed-row">
                  <button
                    className={`play-btn${isPlaying ? ' playing' : ''}`}
                    onClick={() => src && player.togglePlay(src)}
                    title={isPlaying ? 'Pause' : 'Play'}
                  >
                    {isPlaying ? '❚❚' : '▶'}
                  </button>
                  <div className="completed-meta">
                    <div className="completed-title">
                      {t.track_number ? `${t.track_number}. ` : ''}
                      {t.title}
                    </div>
                    <div className="completed-sub">{t.artist}</div>
                  </div>
                  {t.source === 'youtube' && t.output_path && (
                    <button
                      className="finder-link"
                      onClick={() => setEditing(isEditing ? null : t.output_path)}
                    >
                      {isEditing ? 'Close' : 'Edit'}
                    </button>
                  )}
                  {t.output_path && (
                    <button className="finder-link" onClick={() => reveal(t.output_path)}>
                      Show in Finder
                    </button>
                  )}
                </div>
                {isEditing && (
                  <EditTrackForm
                    track={t}
                    onClose={() => setEditing(null)}
                    onSaved={() => {
                      setEditing(null)
                      onChanged && onChanged()
                    }}
                  />
                )}
              </div>
            )
          })}
        </div>
      ))}
    </div>
  )
}
