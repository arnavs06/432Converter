import { api } from '../api.js'

// Group completed tracks (across all jobs) by album for the library view.
export default function Completed({ jobs, player }) {
  const done = []
  jobs.forEach((job) => {
    job.tracks.forEach((t) => {
      if (t.status === 'done') done.push(t)
    })
  })

  if (done.length === 0) return null

  const groups = {}
  done.forEach((t) => {
    const key = `${t.album_artist || t.artist}|||${t.album}`
    if (!groups[key]) {
      groups[key] = {
        album: t.album,
        artist: t.album_artist || t.artist,
        cover: t.cover_url,
        year: t.year,
        tracks: [],
      }
    }
    groups[key].tracks.push(t)
  })

  const reveal = async (path) => {
    if (!path) return
    try {
      await api.reveal(path)
    } catch (e) {
      /* ignore */
    }
  }

  const groupList = Object.entries(groups)

  return (
    <div>
      <div className="section-title">Library · {done.length} tracks</div>
      {groupList.map(([key, group]) => (
        <div className="album-group" key={key}>
          <div className="album-head">
            {group.cover ? (
              <img className="album-head-art" src={group.cover} alt="" />
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
