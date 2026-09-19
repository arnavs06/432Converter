"""YouTube source support via yt-dlp.

Like SoundCloud, YouTube links are downloaded directly: yt-dlp resolves the
metadata and fetches the audio from that exact video. Each track dict carries a
``source_url`` so the converter skips the YouTube search step.
"""
import re
from typing import List

from soundcloud import _year_from_upload_date

_YT_HOSTS = ("youtube.com", "youtu.be", "music.youtube.com")

# Video-title noise to strip, e.g. "(Official Music Video)", "[Lyrics]", "(HD)".
_NOISE_RE = re.compile(
    r"\s*[\(\[][^\)\]]*\b(official|lyrics?|lyric video|audio|video|visuali[sz]er|"
    r"hd|hq|4k|remaster(ed)?|mv|m/v)\b[^\)\]]*[\)\]]",
    re.IGNORECASE,
)


def is_youtube_url(url: str) -> bool:
    lowered = (url or "").lower()
    return any(host in lowered for host in _YT_HOSTS)


def _clean_title(title: str) -> str:
    return _NOISE_RE.sub("", title).strip() or title


def _channel_artist(info: dict) -> str:
    channel = info.get("channel") or info.get("uploader") or ""
    # Auto-generated YouTube Music channels are "Artist - Topic".
    channel = re.sub(r"\s*-\s*Topic$", "", channel)
    channel = re.sub(r"VEVO$", "", channel).strip()
    return channel or "Unknown Artist"


def _artist_and_title(info: dict):
    """Prefer YouTube Music's structured fields, then 'Artist - Title', then channel."""
    raw = info.get("title") or "Unknown Title"
    if info.get("track"):
        artists = info.get("artists") or []
        artist = ", ".join(artists) if artists else info.get("artist") or _channel_artist(info)
        return artist, info["track"]
    for sep in (" - ", " – ", " — "):
        if sep in raw:
            artist, title = raw.split(sep, 1)
            return artist.strip(), _clean_title(title)
    return _channel_artist(info), _clean_title(raw)


def _best_thumbnail(info: dict) -> str:
    """Largest JPEG thumbnail (the cover resizer and ID3 frame expect JPEG)."""
    thumbs = [
        t for t in (info.get("thumbnails") or [])
        if (t.get("url") or "").split("?")[0].endswith(".jpg")
    ]
    if thumbs:
        best = max(thumbs, key=lambda t: (t.get("width") or 0) * (t.get("height") or 0))
        return best["url"]
    vid = info.get("id")
    return f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg" if vid else ""


def _meta_from_entry(info: dict, album: str = "", track_number: int = 0,
                     total_tracks: int = 0) -> dict:
    artist, title = _artist_and_title(info)
    dur = info.get("duration") or 0
    year = str(info.get("release_year") or "") or _year_from_upload_date(
        info.get("upload_date") or ""
    )
    return {
        "title": title,
        "artist": artist,
        "album_artist": artist,
        "album": album or info.get("album") or "YouTube",
        "track_number": track_number,
        "total_tracks": total_tracks,
        "year": year,
        "genre": "",
        "cover_url": _best_thumbnail(info),
        "duration_ms": int(dur * 1000),
        "spotify_id": "",
        "preview_url": "",
        # Direct-download marker consumed by converter.download_audio.
        "source_url": info.get("webpage_url") or info.get("original_url") or "",
    }


def fetch_tracks(url: str) -> List[dict]:
    """Resolve a YouTube video or playlist URL into normalized metadata dicts."""
    import yt_dlp

    opts = {
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
        "extract_flat": False,
        # A watch?v=...&list=... link means "this video"; /playlist links
        # still resolve to the whole playlist.
        "noplaylist": True,
        # Skip private/deleted videos in a playlist instead of failing it.
        "ignoreerrors": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    if not info:
        raise RuntimeError("Could not read that YouTube link.")

    entries = info.get("entries")
    if entries is not None:
        entries = [e for e in entries if e]
        album = info.get("title") or "YouTube Playlist"
        total = len(entries)
        return [
            _meta_from_entry(e, album=album, track_number=i + 1, total_tracks=total)
            for i, e in enumerate(entries)
        ]

    return [_meta_from_entry(info)]
