import { useEffect, useRef, useState } from 'react'
import { api, openSocket } from './api.js'
import InputBar from './components/InputBar.jsx'
import JobCard from './components/JobCard.jsx'
import SettingsPanel from './components/SettingsPanel.jsx'
import SetupModal from './components/SetupModal.jsx'
import StatsBar from './components/StatsBar.jsx'
import Completed from './components/Completed.jsx'

function GearIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  )
}

export default function App() {
  const [config, setConfig] = useState(null)
  const [needsSetup, setNeedsSetup] = useState(false)
  const [showSettings, setShowSettings] = useState(false)
  const [jobs, setJobs] = useState([])
  const [stats, setStats] = useState(null)
  const [albums, setAlbums] = useState([])
  const wsRef = useRef(null)
  const audioRef = useRef(null)
  const [playingSrc, setPlayingSrc] = useState('')

  // Toggle inline playback: clicking the active track pauses, otherwise plays.
  const togglePlay = (src) => {
    if (!src) return
    const el = audioRef.current
    if (!el) return
    if (playingSrc === src) {
      el.pause()
      setPlayingSrc('')
      return
    }
    el.src = src
    el.play().then(() => setPlayingSrc(src)).catch(() => setPlayingSrc(''))
  }
  const player = { playingSrc, togglePlay }

  // Queue shows jobs still in flight (or with retryable errors); fully-done
  // jobs live only in the Completed library below. Cancelled tracks are dropped
  // from the queue, so a job that's all done-or-cancelled disappears too.
  const activeJobs = jobs.filter((j) =>
    j.tracks.some((t) => t.status !== 'done' && t.status !== 'cancelled')
  )

  // Merge a single track update into the jobs list.
  const applyTrackUpdate = (jobId, idx, track) => {
    setJobs((prev) =>
      prev.map((job) => {
        if (job.job_id !== jobId) return job
        const tracks = job.tracks.slice()
        if (tracks[idx]) tracks[idx] = { ...tracks[idx], ...track }
        return { ...job, tracks }
      })
    )
  }

  const refreshJobs = async () => {
    try {
      const list = await api.getJobs()
      setJobs(list)
    } catch (e) {
      /* ignore */
    }
  }

  const refreshStats = async () => {
    try {
      setStats(await api.getStats())
    } catch (e) {
      /* ignore */
    }
  }

  const refreshLibrary = async () => {
    try {
      const { albums } = await api.getLibrary()
      setAlbums(albums || [])
    } catch (e) {
      /* ignore */
    }
  }

  // Initial load: config, jobs, stats + open websocket.
  useEffect(() => {
    ;(async () => {
      try {
        const cfg = await api.getConfig()
        setConfig(cfg)
        setNeedsSetup(!cfg.configured)
      } catch (e) {
        setNeedsSetup(true)
      }
      refreshJobs()
      refreshStats()
      refreshLibrary()
    })()

    const ws = openSocket((msg) => {
      if (msg.type === 'init') {
        if (Array.isArray(msg.jobs)) setJobs(msg.jobs)
      } else if (msg.type === 'track_update') {
        applyTrackUpdate(msg.job_id, msg.track_index, msg.track)
        // A track finishing adds a new file to the library.
        if (msg.track && msg.track.status === 'done') {
          refreshStats()
          refreshLibrary()
        }
      } else if (msg.type === 'job_created') {
        refreshJobs()
      } else if (msg.type === 'job_done') {
        refreshStats()
        refreshLibrary()
      }
    })
    wsRef.current = ws
    return () => ws.close()
  }, [])

  const handleConvert = async (url) => {
    await api.convert(url)
    await refreshJobs()
  }

  const handleSaveConfig = async (values) => {
    const cfg = await api.saveConfig(values)
    setConfig(cfg)
    return cfg
  }

  const handleSetupSave = async (values) => {
    const cfg = await handleSaveConfig(values)
    if (cfg.configured) setNeedsSetup(false)
  }

  const handleRetry = async (jobId, idx, override) => {
    applyTrackUpdate(jobId, idx, { status: 'queued', error: '', warning: '' })
    try {
      await api.retry(jobId, idx, override)
    } catch (e) {
      /* ignore */
    }
  }

  const handleCancel = async (jobId, idx) => {
    applyTrackUpdate(jobId, idx, { status: 'cancelled', error: '', warning: '' })
    try {
      await api.cancel(jobId, idx)
    } catch (e) {
      /* ignore */
    }
  }

  return (
    <div>
      <div className="topbar">
        <div className="app-name">
          432 <span className="hz">Converter</span>
        </div>
        <button className="gear-btn" onClick={() => setShowSettings((s) => !s)} title="Settings">
          <GearIcon />
        </button>
      </div>

      {showSettings && config && (
        <SettingsPanel config={config} onSave={handleSaveConfig} />
      )}

      <div className="page">
        <InputBar onConvert={handleConvert} />

        {activeJobs.length > 0 && (
          <>
            <div className="section-title">Queue</div>
            {activeJobs.map((job) => (
              <JobCard key={job.job_id} job={job} onRetry={handleRetry} onCancel={handleCancel} player={player} />
            ))}
          </>
        )}

        {activeJobs.length === 0 && albums.length === 0 && (
          <div className="empty-state">
            <div className="empty-fork">🎵</div>
            <div className="empty-title">Retune anything to 432&nbsp;Hz</div>
            <div className="empty-sub">
              Paste a Spotify track, album, or playlist link above and it lands in
              your library — pitch-shifted, tagged, and ready for Spotify Local Files.
            </div>
          </div>
        )}

        <Completed albums={albums} player={player} />
      </div>

      <audio ref={audioRef} onEnded={() => setPlayingSrc('')} hidden />
      <StatsBar stats={stats} />

      {needsSetup && <SetupModal onSave={handleSetupSave} />}
    </div>
  )
}
