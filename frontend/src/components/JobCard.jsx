import TrackRow from './TrackRow.jsx'

export default function JobCard({ job, onRetry, player }) {
  const done = job.tracks.filter((t) => t.status === 'done').length
  const total = job.tracks.length
  const pct = total ? Math.round((done / total) * 100) : 0

  return (
    <div className="job-card">
      <div className="job-card-header">
        <div className="job-card-title">
          {total} {total === 1 ? 'track' : 'tracks'} · {done} done
        </div>
        <div className="job-card-pct">{pct}%</div>
      </div>
      {job.tracks.map((track, idx) => (
        <TrackRow
          key={idx}
          track={track}
          onRetry={(override) => onRetry(job.job_id, idx, override)}
          player={player}
        />
      ))}
    </div>
  )
}
