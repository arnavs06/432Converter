import { api } from '../api.js'

// Group completed tracks (across all jobs) by album for the library view.
export default function Completed({ jobs }) {
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

  return (
    <div>
      <div className="section-title">Completed</div>
      {Object.entries(groups).map(([key, group]) => (
        <div className="album-group" key={key}>
          <div className="album-group-title">
            {group.album || 'Unknown Album'} — {group.artist}
          </div>
          {group.tracks.map((t, i) => (
            <div className="completed-row" key={i}>
              {t.cover_url ? (
                <img className="completed-art" src={t.cover_url} alt="" />
              ) : (
                <div className="completed-art" />
              )}
              <div className="completed-meta">
                <div className="completed-title">
                  {t.track_number ? `${t.track_number}. ` : ''}
                  {t.title}
                </div>
                <div className="completed-sub">
                  {t.artist} · {t.album}
                </div>
              </div>
              {t.output_path && (
                <button className="finder-link" onClick={() => reveal(t.output_path)}>
                  Show in Finder
                </button>
              )}
            </div>
          ))}
        </div>
      ))}
    </div>
  )
}
