# 432 Converter

A local web app that converts Spotify tracks, albums, and playlists into
**432 Hz MP3s** with complete ID3 metadata and album art — ready to drop into
Spotify's **Local Files**.

The pipeline is fully deterministic (no AI): it reads metadata from the Spotify
API, downloads the best matching audio from YouTube, transcodes to 192 kbps MP3,
pitch-shifts to 432 Hz, and writes tagged files organized as
`Artist/Album/NN - Title.mp3`.

---

## Requirements

- **Python 3.9+**
- **Node.js 18+**
- **ffmpeg** on your `PATH`
  - macOS: `brew install ffmpeg`
  - Windows: `choco install ffmpeg` (or download from [ffmpeg.org](https://ffmpeg.org/download.html))

## Quick start

### macOS / Linux

```bash
./start.sh
```

This installs Python and npm dependencies, starts the FastAPI backend on
`http://localhost:8000`, starts the Vite dev server on `http://localhost:5173`,
and opens your browser.

### Windows

Run the two servers manually:

```bat
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

In a second terminal:

```bat
cd frontend
npm install
npm run dev
```

Then open <http://localhost:5173>.

---

## Getting Spotify API credentials

1. Go to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard).
2. Log in and click **Create app**.
3. Give it any name and description. For the redirect URI you can use
   `http://localhost:8000` (it is not used by this app, but the form requires one).
4. Open the app's **Settings** and copy the **Client ID** and **Client Secret**.
5. On first launch, 432 Converter shows a setup modal — paste both values and
   click **Save & Continue**. You can change them later from the gear ⚙️ menu.

Credentials and settings are stored locally at `~/.432converter/config.json`.

---

## Using the app

1. Paste a Spotify **track**, **album**, or **playlist** link into the input bar
   and press **Convert**.
2. Watch per-track progress: Queued → Downloading → Converting → Tagging → Done ✓.
3. Failed tracks show a red ✗ with the error and a **Retry** button. If the
   matched YouTube title looks wrong, a warning lets you override the search
   query and retry.
4. Completed tracks are grouped by album with **Show in Finder** links.

### Settings (gear ⚙️)

- **Output directory** — where MP3s are written (default `~/Music/432hz`).
- **Spotify Client ID / Secret**.
- **Delay between tracks** — throttle to avoid rate limits.

All settings save automatically.

---

## Adding the output folder to Spotify Local Files

1. Open the Spotify desktop app.
2. Go to **Settings** (top-right profile → Settings).
3. Scroll to **Local Files** and enable **Show Local Files**.
4. Click **Add a source** and select your output folder (default
   `~/Music/432hz`).
5. The 432 Hz tracks — with full titles, artists, album art, and track numbers —
   appear under **Your Library → Local Files**. Add them to a playlist and, on
   mobile, download that playlist to sync the local files to your phone.

---

## How the 432 Hz shift works

Standard tuning is A = 440 Hz. To retune to A = 432 Hz, every frequency is
shifted by:

```
n_steps = 12 * log2(432 / 440) ≈ -0.3176 semitones
```

`librosa.effects.pitch_shift` applies this shift (mono and stereo handled
per-channel), `soundfile` writes the result, and ffmpeg re-encodes to a
192 kbps MP3 before tagging with `mutagen`.

---

## Project structure

```
backend/
  main.py          FastAPI app: jobs, WebSocket, config, retry, stats
  converter.py     Download → MP3 → 432 Hz → ID3 tag pipeline
  spotify.py       Spotify metadata fetching (track/album/playlist)
  config.py        ~/.432converter/config.json load & save
  requirements.txt
frontend/
  src/
    App.jsx
    api.js
    components/    InputBar, JobCard, TrackRow, SettingsPanel, SetupModal, StatsBar, Completed
start.sh
```

## Notes

- Conversions run on a background thread pool; the API stays responsive.
- Job state is in memory only (no database). Restarting the backend clears the
  queue, but already-written files are kept and skipped on re-runs.
- For personal use only. Respect copyright and the terms of service of the
  platforms you use.
