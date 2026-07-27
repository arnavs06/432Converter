"""SoundCloud source support via yt-dlp.

Unlike the Spotify flow (metadata lookup + YouTube search), SoundCloud links are
downloaded directly: yt-dlp both resolves the metadata and fetches the audio from
the same URL. Each track dict carries a ``source_url`` so the converter downloads
that exact track instead of searching YouTube.
"""
from typing import List


def is_soundcloud_url(url: str) -> bool:
    return "soundcloud.com" in (url or "").lower()


def _year_from_upload_date(upload_date: str) -> str:
    # yt-dlp gives upload_date as YYYYMMDD.
    if upload_date and len(upload_date) >= 4 and upload_date[:4].isdigit():
        return upload_date[:4]
    return ""


def _best_thumbnail(info: dict) -> str:
    """Pick the largest available artwork URL."""
    thumbs = info.get("thumbnails") or []
    if thumbs:
        # yt-dlp orders thumbnails smallest -> largest.
        url = thumbs[-1].get("url")
        if url:
            # SoundCloud serves squares like ...-large.jpg (100px); bump to the
            # 500px variant when we recognize the pattern.
            return url.replace("-large.", "-t500x500.")
    return info.get("thumbnail") or ""


def _meta_from_entry(info: dict, album: str = "", track_number: int = 0,
                     total_tracks: int = 0) -> dict:
    title = info.get("title") or "Unknown Title"
    artist = (
        info.get("uploader")
        or info.get("uploader_id")
        or info.get("channel")
        or "Unknown Artist"
    )
    dur = info.get("duration") or 0
    return {
        "title": title,
        "artist": artist,
        "album_artist": artist,
        "album": album or info.get("album") or "SoundCloud",
        "track_number": track_number,
        "total_tracks": total_tracks,
        "year": _year_from_upload_date(info.get("upload_date") or ""),
        "genre": info.get("genre") or "",
        "cover_url": _best_thumbnail(info),
        "duration_ms": int(dur * 1000),
        "spotify_id": "",
        "preview_url": "",
        # Direct-download marker consumed by converter.download_audio.
        "source_url": info.get("webpage_url") or info.get("url") or "",
    }


def fetch_tracks(url: str) -> List[dict]:
    """Resolve a SoundCloud track or set URL into normalized metadata dicts."""
    import yt_dlp

    opts = {
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
        "extract_flat": False,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

    entries = info.get("entries")
    if entries is not None:
        # A set / playlist.
        entries = [e for e in entries if e]
        album = info.get("title") or "SoundCloud Set"
        total = len(entries)
        return [
            _meta_from_entry(e, album=album, track_number=i + 1, total_tracks=total)
            for i, e in enumerate(entries)
        ]

    return [_meta_from_entry(info)]
