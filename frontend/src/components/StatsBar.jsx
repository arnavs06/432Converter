export default function StatsBar({ stats }) {
  if (!stats) return null
  const { count, size_gb, output_dir } = stats
  return (
    <div className="stats-bar">
      {count} {count === 1 ? 'track' : 'tracks'} converted · {size_gb} GB · {output_dir}
    </div>
  )
}
