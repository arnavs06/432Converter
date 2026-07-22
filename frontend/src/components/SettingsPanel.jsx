import { useEffect, useRef, useState } from 'react'

export default function SettingsPanel({ config, onSave }) {
  const [outputDir, setOutputDir] = useState(config.output_dir || '')
  const [clientId, setClientId] = useState(config.SPOTIFY_CLIENT_ID || '')
  const [clientSecret, setClientSecret] = useState(config.SPOTIFY_CLIENT_SECRET || '')
  const [delay, setDelay] = useState(config.delay_between_tracks ?? 2)
  const [saved, setSaved] = useState(false)
  const savedTimer = useRef(null)

  useEffect(() => {
    setOutputDir(config.output_dir || '')
    setClientId(config.SPOTIFY_CLIENT_ID || '')
    setClientSecret(config.SPOTIFY_CLIENT_SECRET || '')
    setDelay(config.delay_between_tracks ?? 2)
  }, [config])

  const flashSaved = () => {
    setSaved(true)
    clearTimeout(savedTimer.current)
    savedTimer.current = setTimeout(() => setSaved(false), 1600)
  }

  const persist = async (values) => {
    await onSave(values)
    flashSaved()
  }

  return (
    <div className="settings-panel">
      <div className="settings-inner">
        <div className="field">
          <label>Output directory</label>
          <input
            type="text"
            value={outputDir}
            onChange={(e) => setOutputDir(e.target.value)}
            onBlur={() => persist({ output_dir: outputDir })}
            placeholder="~/Music/432hz"
          />
          <div className="hint">
            Add this folder to Spotify → Settings → Local Files.
          </div>
        </div>

        <div className="field">
          <label>Spotify Client ID</label>
          <input
            type="text"
            value={clientId}
            onChange={(e) => setClientId(e.target.value)}
            onBlur={() => persist({ SPOTIFY_CLIENT_ID: clientId })}
          />
        </div>

        <div className="field">
          <label>Spotify Client Secret</label>
          <input
            type="password"
            value={clientSecret}
            onChange={(e) => setClientSecret(e.target.value)}
            onBlur={() => persist({ SPOTIFY_CLIENT_SECRET: clientSecret })}
          />
          <div className="hint">
            Create an app at{' '}
            <a href="https://developer.spotify.com/dashboard" target="_blank" rel="noreferrer">
              developer.spotify.com
            </a>
            .
          </div>
        </div>

        <div className="field">
          <label>Delay between tracks</label>
          <div className="slider-row">
            <input
              type="range"
              min="0"
              max="10"
              step="0.5"
              value={delay}
              onChange={(e) => setDelay(parseFloat(e.target.value))}
              onMouseUp={() => persist({ delay_between_tracks: delay })}
              onTouchEnd={() => persist({ delay_between_tracks: delay })}
            />
            <span className="slider-value">{delay.toFixed(1)}s</span>
          </div>
        </div>

        <span className={`saved-tag${saved ? ' show' : ''}`}>Saved ✓</span>
      </div>
    </div>
  )
}
