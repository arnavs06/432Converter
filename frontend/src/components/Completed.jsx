import { api } from '../api.js'

// Library view built from the actual files on disk (via /api/library), so
// every converted track shows up regardless of job history.
export default function Completed({ albums, player }) {
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
            return (
              <div className="completed-row" key={i}>
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
                {t.output_path && (
                  <button className="finder-link" onClick={() => reveal(t.output_path)}>
                    Show in Finder
                  </button>
                )}
              </div>
            )
          })}
        </div>
      ))}
    </div>
  )
}
