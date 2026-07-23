# 432 Converter

A local web app that converts Spotify tracks, albums, and playlists into
**432 Hz MP3s** with complete ID3 metadata and album art — ready to drop into
Spotify's **Local Files** (and Apple Music / YouTube Music).

The pipeline is fully deterministic (no AI): it reads metadata from the Spotify
API, downloads the best matching audio from YouTube, retunes to 432 Hz, and
writes tagged files organized as `Artist/Album/NN - Title (432Hz).mp3`.

---

## Features

- **One clean 320 kbps pass** — retunes to 432 Hz by resampling (the "turntable"
  method) in a single ffmpeg encode. No phase-vocoder smearing, no double
  encoding.
- **Full ID3v2.3 tags + album art** — title, artist, album artist, album, track
  number, year, genre, and embedded cover.
- **"(432Hz)" marker** appended to every title and filename so retuned tracks are
  easy to spot in any player.
- **DRM-resilient downloads** — tries several YouTube results and skips
  DRM-protected / private / unavailable ones instead of failing.
- **Live progress** over WebSocket: Queued → Downloading → Converting → Tagging →
  Done ✓, with per-track retry and a YouTube-search override for bad matches.
- **Library view** built from the files on disk (not just session history), with
  album grouping, cover art, and inline **play/pause previews** of the converted
  audio.
- **Persistent history** — jobs survive restarts.
- **Auto playlist** — writes an `[Album] 432Hz.m3u8` per album on download.

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

1. Go to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
   and click **Create app**.
2. Give it any name and description. Check **Web API**. For the redirect URI use
   `http://127.0.0.1:8000` — it isn't used by this app, but the form requires a
   valid loopback URI (Spotify rejects `http://localhost`).
3. Open the app's **Settings** and copy the **Client ID**, then **View client
   secret**.
4. On first launch, 432 Converter shows a setup modal — paste both values and
   click **Save & Continue**. You can change them later from the gear ⚙️ menu.

The app uses the Client Credentials flow (app-only, read-only metadata), so no
user login is needed. Credentials and settings are stored locally at
`~/.432converter/config.json`.

---

## Using the app

1. Paste a Spotify **track**, **album**, or **playlist** link into the input bar
   and press **Convert**.
2. Watch per-track progress. Failed tracks show a red ✗ with the error and a
   **Retry** button. If the matched YouTube title looks wrong, a warning lets you
   override the search query and retry.
3. Finished tracks appear in the **Library**, grouped by album, with a
   **play/pause** button (streams the converted file) and a **Show in Finder**
   link.

### Settings (gear ⚙️)

- **Output directory** — where MP3s are written (default `~/Music/432hz`).
- **Spotify Client ID / Secret**.
- **Delay between tracks** — throttle to avoid rate limits.

All settings save automatically.

---

## Getting the tracks onto your phone

The files are standard tagged MP3s, so they work with any service that supports
local files or uploads.

| Service | Songs | Auto `.m3u` playlist |
| --- | --- | --- |
| **Apple Music** | ✅ Drag into the Music app | ✅ File → Import Playlist |
| **Spotify** | ✅ Add folder as a Local Files source | ❌ Rebuild playlist manually |
| **YouTube Music** | ✅ Upload at music.youtube.com | ❌ Rebuild playlist manually |

### Spotify Local Files

1. Spotify desktop → **Settings** → **Local Files** → enable **Show Local Files**.
2. **Add a source** and select your output folder (default `~/Music/432hz`).
3. The 432 Hz tracks appear under **Your Library → Local Files**. Add them to a
   playlist, then on mobile **download that playlist** to sync the files to your
   phone.

> Spotify can't import `.m3u` playlist files, so the playlist step is manual.
> Spotify ignores the generated `.m3u8` files entirely — they don't affect Local
> Files.

---

## How the 432 Hz retune works

Standard tuning is A = 440 Hz. Retuning to A = 432 Hz means lowering every
frequency by a factor of `432 / 440` (≈ 0.32 of a semitone). Instead of a
phase-vocoder pitch shift (which smears transients), the app **resamples** — the
same operation as playing a record slightly slower — via a single ffmpeg pass:

```
-af "aresample=44100,asetrate=43298,aresample=44100"   # 43298 = 44100 * 432/440
```

This is artifact-free and is the authentic 432 Hz "turntable" retune; the track
ends up ~1.9% longer. ffmpeg then encodes to a 320 kbps MP3 and `mutagen` writes
the ID3v2.3 tags and cover art.

**A note on the effect:** 440 → 432 is a very small change (~0.32 semitone). Most
people can't reliably distinguish it in a blind test, and there's no established
scientific evidence that 432 Hz is objectively "better." Audio quality is capped
by the YouTube source (~128–160 kbps), so results are comparable to Spotify's
normal quality rather than a Premium 320 kbps stream.

---

## Project structure

```
backend/
  main.py          FastAPI app: jobs, WebSocket, config, retry, stats,
                   library scan, audio/cover streaming, playlist generation
  converter.py     Download → 432 Hz resample → 320k MP3 → ID3 tag pipeline
  spotify.py       Spotify metadata fetching (track/album/playlist)
  config.py        ~/.432converter/{config,jobs}.json load & save
  requirements.txt
frontend/
  src/
    App.jsx
    api.js
    components/    InputBar, JobCard, TrackRow, SettingsPanel,
                   SetupModal, StatsBar, Completed
start.sh
```

## Notes

- Conversions run on a background thread pool; the API stays responsive.
- Job history is persisted to `~/.432converter/jobs.json`; the **Library** is
  read from the actual files on disk, so earlier downloads always show up.
  Already-converted files are skipped on re-runs.
- For personal use only. Respect copyright and the terms of service of the
  platforms you use.
```
