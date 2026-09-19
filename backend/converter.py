"""Core conversion pipeline: YouTube download -> MP3 -> 432 Hz -> ID3 tags.

Deterministic, no AI. Each stage updates a per-track status callback so the
API/WebSocket layer can stream progress.
"""
import os
import re
import shutil
import subprocess
import tempfile
from difflib import SequenceMatcher
from pathlib import Path

import requests
from mutagen.id3 import (
    APIC,
    ID3,
    TALB,
    TCON,
    TDRC,
    TIT2,
    TPE1,
    TPE2,
    TRCK,
)


def _safe_name(name: str) -> str:
    """Sanitize a string for use as a file/folder name across macOS + Windows."""
    name = (name or "").strip()
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    name = name.rstrip(". ")
    return name or "Unknown"


# Marker appended to every title so 432 Hz tracks are recognizable in players.
TITLE_SUFFIX = " (432Hz)"


def display_title(meta: dict) -> str:
    """Track title with the 432Hz marker, without doubling it up."""
    title = (meta.get("title") or "Unknown Title").strip()
    if "432hz" in title.lower().replace(" ", ""):
        return title
    return f"{title}{TITLE_SUFFIX}"


def output_path_for(output_dir: str, meta: dict) -> Path:
    """Compute output_dir/Artist/Album/NN - Title (432Hz).mp3 for a track."""
    artist = _safe_name(meta.get("album_artist") or meta.get("artist"))
    album = _safe_name(meta.get("album") or "Unknown Album")
    title = _safe_name(display_title(meta))
    tn = meta.get("track_number") or 0
    filename = f"{int(tn):02d} - {title}.mp3" if tn else f"{title}.mp3"
    return Path(output_dir) / artist / album / filename


def _fuzzy_ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, (a or "").lower(), (b or "").lower()).ratio()


def _find_ffmpeg() -> str:
    return shutil.which("ffmpeg") or "ffmpeg"


# How many YouTube results to consider before giving up.
_SEARCH_CANDIDATES = 6

# Substrings in a yt-dlp error that mean "try the next result", not "abort".
_SKIPPABLE_ERRORS = (
    "drm",
    "video unavailable",
    "private video",
    "sign in",
    "members-only",
    "removed",
    "not available",
    "age",
)


def _source_file(tmp_dir: str):
    for f in os.listdir(tmp_dir):
        if f.startswith("source."):
            return os.path.join(tmp_dir, f)
    return None


def download_audio(meta: dict, tmp_dir: str, query_override: str = None):
    """Search YouTube and download best audio. Returns (audio_path, yt_title).

    Tries several search results in order, skipping ones that are DRM-protected,
    private, or otherwise undownloadable, so one bad top hit doesn't fail the
    track. Raises RuntimeError only if every candidate fails.
    """
    import yt_dlp

    out_template = os.path.join(tmp_dir, "source.%(ext)s")

    dl_opts_base = {
        "format": "bestaudio/best",
        "outtmpl": out_template,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
    }

    # Direct-download sources (e.g. SoundCloud) carry an exact URL, so skip the
    # YouTube search entirely and pull that track. A manual query_override still
    # forces a fresh YouTube search (used by the retry-with-different-search UI).
    source_url = meta.get("source_url")
    if source_url and not query_override:
        with yt_dlp.YoutubeDL(dl_opts_base) as ydl:
            info = ydl.extract_info(source_url, download=True)
        downloaded = _source_file(tmp_dir)
        if downloaded and os.path.exists(downloaded):
            return downloaded, info.get("title", meta.get("title", ""))
        raise RuntimeError("Source download produced no file.")

    if query_override:
        query = query_override
    else:
        query = f"{meta.get('artist', '')} {meta.get('title', '')} audio".strip()

    # First pass: a flat search just to enumerate candidate videos cheaply.
    search_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "nocheckcertificate": True,
    }
    with yt_dlp.YoutubeDL(search_opts) as ydl:
        results = ydl.extract_info(
            f"ytsearch{_SEARCH_CANDIDATES}:{query}", download=False
        )
    candidates = [e for e in (results.get("entries") or []) if e]
    if not candidates:
        raise RuntimeError("No YouTube result found.")

    dl_opts = dl_opts_base

    last_error = ""
    for cand in candidates:
        video_url = cand.get("url") or cand.get("webpage_url") or cand.get("id")
        if not video_url:
            continue
        # Clear any partial file from a previous failed attempt.
        stale = _source_file(tmp_dir)
        if stale:
            try:
                os.remove(stale)
            except OSError:
                pass
        try:
            with yt_dlp.YoutubeDL(dl_opts) as ydl:
                info = ydl.extract_info(video_url, download=True)
            yt_title = info.get("title", cand.get("title", ""))
            downloaded = _source_file(tmp_dir)
            if downloaded and os.path.exists(downloaded):
                return downloaded, yt_title
            last_error = "Download produced no file."
        except Exception as exc:  # noqa: BLE001 - decide skip vs. abort below
            msg = str(exc)
            last_error = msg
            if any(tok in msg.lower() for tok in _SKIPPABLE_ERRORS):
                continue  # try the next candidate
            # Non-skippable (e.g. network); keep trying others but remember it.
            continue

    raise RuntimeError(f"All YouTube candidates failed. Last error: {last_error}")


def title_matches(meta: dict, yt_title: str) -> bool:
    """Loose check that the YouTube title relates to the track title."""
    title = (meta.get("title") or "").lower()
    yt = (yt_title or "").lower()
    if not title:
        return True
    if title in yt:
        return True
    return _fuzzy_ratio(title, yt) >= 0.45


# Output settings.
TARGET_SR = 44100
OUTPUT_BITRATE = "320k"
# 432 Hz retune as a resample ("turntable") shift: reinterpret the samples at
# a slightly lower rate, then resample back. This changes pitch by exactly
# 432/440 with no phase-vocoder smearing, so it stays clean. The track ends up
# ~1.9% longer, which is the authentic 432 Hz slowdown.
_SHIFTED_SR = round(TARGET_SR * 432 / 440)  # 43298
_AF_432 = f"aresample={TARGET_SR},asetrate={_SHIFTED_SR},aresample={TARGET_SR}"


def convert_to_432hz_mp3(src_path: str, tmp_dir: str) -> str:
    """Retune to 432 Hz and encode to a 320 kbps MP3 in one ffmpeg pass.

    Single lossy encode + resample-based pitch shift keeps quality high
    (no phase vocoder, no intermediate MP3 generation).
    """
    final = os.path.join(tmp_dir, "final.mp3")
    cmd = [
        _find_ffmpeg(),
        "-y",
        "-i", src_path,
        "-vn",
        "-af", _AF_432,
        "-codec:a", "libmp3lame",
        "-b:a", OUTPUT_BITRATE,
        final,
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0 or not os.path.exists(final):
        err = proc.stderr.decode("utf-8", "ignore")[-500:]
        raise RuntimeError(f"ffmpeg 432Hz conversion failed: {err}")
    return final


def _fetch_cover(url: str) -> bytes:
    if not url:
        return b""
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        return resp.content
    except Exception:
        return b""


def _resize_cover(data: bytes, size: int = 300) -> bytes:
    """Center-crop JPEG cover bytes to a square and downscale to size x size with
    ffmpeg (square art is untouched by the crop; 16:9 video thumbnails aren't
    squashed). Returns b'' on failure."""
    if not data:
        return b""
    tmp_dir = tempfile.mkdtemp(prefix="cover_")
    src = os.path.join(tmp_dir, "in.jpg")
    out = os.path.join(tmp_dir, "out.jpg")
    try:
        with open(src, "wb") as fh:
            fh.write(data)
        proc = subprocess.run(
            [_find_ffmpeg(), "-y", "-i", src, "-vf", f"crop=min(iw\\,ih):min(iw\\,ih),scale={size}:{size}", "-q:v", "3", out],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        if proc.returncode == 0 and os.path.exists(out):
            with open(out, "rb") as fh:
                return fh.read()
        return b""
    except OSError:
        return b""
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def embed_tags(mp3_path: str, meta: dict) -> None:
    """Write ID3v2.3 tags and album art onto the MP3 in place."""
    try:
        tags = ID3(mp3_path)
    except Exception:
        tags = ID3()

    tags.delall("TIT2")
    tags.delall("TPE1")
    tags.delall("TPE2")
    tags.delall("TALB")
    tags.delall("TRCK")
    tags.delall("TYER")
    tags.delall("TDRC")
    tags.delall("TCON")
    tags.delall("APIC")

    tags.add(TIT2(encoding=3, text=display_title(meta)))
    tags.add(TPE1(encoding=3, text=meta.get("artist", "")))
    tags.add(TPE2(encoding=3, text=meta.get("album_artist", "")))
    tags.add(TALB(encoding=3, text=meta.get("album", "")))

    tn = meta.get("track_number") or 0
    total = meta.get("total_tracks") or 0
    trck = f"{tn}/{total}" if total else str(tn)
    tags.add(TRCK(encoding=3, text=trck))

    year = str(meta.get("year") or "")
    if year:
        # mutagen canonicalizes the year to TDRC; on a v2.3 save it emits the
        # matching TYER frame on disk, so we only need to set TDRC here.
        tags.add(TDRC(encoding=3, text=year))

    genre = meta.get("genre") or ""
    if genre:
        tags.add(TCON(encoding=3, text=genre))

    art = _fetch_cover(meta.get("cover_url", ""))
    if art:
        # Small (300x300) square cover with an empty description renders more
        # reliably in Spotify Local Files than the full 640x640 image.
        art = _resize_cover(art) or art
        tags.add(APIC(
            encoding=3,
            mime="image/jpeg",
            type=3,  # front cover
            desc="",
            data=art,
        ))

    tags.save(mp3_path, v2_version=3)


def convert_track(meta: dict, output_dir: str, status_cb, query_override: str = None) -> dict:
    """Run the full pipeline for one track.

    status_cb(stage, extra) is called with stages:
      downloading, converting, tagging, done, error, skipped, warning
    Returns a result dict with keys: status, output_path, error, yt_title.
    """
    result = {"status": "queued", "output_path": "", "error": "", "yt_title": ""}

    final_path = output_path_for(output_dir, meta)
    result["output_path"] = str(final_path)

    if final_path.exists():
        result["status"] = "done"
        status_cb("done", {"output_path": str(final_path), "skipped": True})
        return result

    tmp_dir = tempfile.mkdtemp(prefix="432conv_")
    try:
        # 1. Download
        status_cb("downloading", {})
        src, yt_title = download_audio(meta, tmp_dir, query_override)
        result["yt_title"] = yt_title

        if not title_matches(meta, yt_title) and not query_override:
            status_cb("warning", {"yt_title": yt_title})

        # 2. Retune to 432 Hz and encode to 320k MP3 in a single pass.
        status_cb("converting", {})
        final_mp3 = convert_to_432hz_mp3(src, tmp_dir)

        # 3. Move into place
        final_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(final_mp3, str(final_path))

        # 4. Tag
        status_cb("tagging", {})
        embed_tags(str(final_path), meta)

        result["status"] = "done"
        status_cb("done", {"output_path": str(final_path), "skipped": False})
        return result

    except Exception as exc:  # noqa: BLE001 - errors are surfaced per-track
        result["status"] = "error"
        result["error"] = str(exc)
        status_cb("error", {"error": str(exc)})
        return result
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
