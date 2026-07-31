import TrackRow from './TrackRow.jsx'

export default function JobCard({ job, onRetry, onCancel, player }) {
  // Keep each track's original index (retry/cancel reference it) while hiding
  // cancelled tracks from the card.
  const visible = job.tracks
    .map((track, idx) => ({ track, idx }))
    .filter(({ track }) => track.status !== 'cancelled')
  const done = visible.filter(({ track }) => track.status === 'done').length
  const total = visible.length
  const pct = total ? Math.round((done / total) * 100) : 0

  return (
    <div className="job-card">
      <div className="job-card-header">
        <div className="job-card-title">
          {total} {total === 1 ? 'track' : 'tracks'} · {done} done
        </div>
        <div className="job-card-pct">{pct}%</div>
      </div>
      {visible.map(({ track, idx }) => (
        <TrackRow
          key={idx}
          track={track}
          onRetry={(override) => onRetry(job.job_id, idx, override)}
          onCancel={() => onCancel(job.job_id, idx)}
          player={player}
        />
      ))}
    </div>
  )
}
