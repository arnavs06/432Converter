import TrackRow from './TrackRow.jsx'

export default function JobCard({ job, onRetry }) {
  const done = job.tracks.filter((t) => t.status === 'done').length
  const total = job.tracks.length

  return (
    <div className="job-card">
      <div className="job-card-header">
        <div className="job-card-title">
          {total} {total === 1 ? 'track' : 'tracks'} · {done} done
        </div>
      </div>
      {job.tracks.map((track, idx) => (
        <TrackRow
          key={idx}
          track={track}
          onRetry={(override) => onRetry(job.job_id, idx, override)}
        />
      ))}
    </div>
  )
}
