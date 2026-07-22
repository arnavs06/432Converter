"""Spotify metadata fetching via spotipy.

Given a Spotify URL (track, album, or playlist) this returns a normalized list
of track metadata dicts used by the converter pipeline.
"""
import re
from typing import List

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

from config import load_config

_URL_RE = re.compile(r"open\.spotify\.com/(?:intl-[a-z]+/)?(track|album|playlist)/([A-Za-z0-9]+)")
_URI_RE = re.compile(r"spotify:(track|album|playlist):([A-Za-z0-9]+)")


def parse_spotify_url(url: str):
    """Return (kind, spotify_id) for a track/album/playlist URL or URI."""
    url = (url or "").strip()
    m = _URL_RE.search(url)
    if not m:
        m = _URI_RE.search(url)
    if not m:
        raise ValueError("Not a valid Spotify track, album, or playlist URL.")
    return m.group(1), m.group(2)


def _client() -> spotipy.Spotify:
    cfg = load_config()
    client_id = cfg.get("SPOTIFY_CLIENT_ID")
    client_secret = cfg.get("SPOTIFY_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError("Spotify credentials are not configured.")
    auth = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
    return spotipy.Spotify(client_credentials_manager=auth, requests_timeout=30)


def _year_from_date(date_str: str) -> str:
    if not date_str:
        return ""
    return date_str.split("-")[0]


def _genre_for_artist(sp: spotipy.Spotify, artist_id: str) -> str:
    try:
        artist = sp.artist(artist_id)
        genres = artist.get("genres") or []
        return genres[0].title() if genres else ""
    except Exception:
        return ""


def _track_from_full(sp, track, album, genre_cache) -> dict:
    """Build a normalized metadata dict from a full track object + album object."""
    artists = track.get("artists") or []
    artist = ", ".join(a["name"] for a in artists) if artists else "Unknown Artist"
    album_artists = album.get("artists") or artists
    album_artist = album_artists[0]["name"] if album_artists else artist

    images = album.get("images") or []
    cover_url = images[0]["url"] if images else ""

    primary_artist_id = artists[0]["id"] if artists else None
    genre = ""
    if primary_artist_id:
        if primary_artist_id not in genre_cache:
            genre_cache[primary_artist_id] = _genre_for_artist(sp, primary_artist_id)
        genre = genre_cache[primary_artist_id]

    return {
        "title": track.get("name", ""),
        "artist": artist,
        "album_artist": album_artist,
        "album": album.get("name", ""),
        "track_number": track.get("track_number", 0),
        "total_tracks": album.get("total_tracks", 0),
        "year": _year_from_date(album.get("release_date", "")),
        "genre": genre,
        "cover_url": cover_url,
        "duration_ms": track.get("duration_ms", 0),
        "spotify_id": track.get("id", ""),
    }


def fetch_tracks(url: str) -> List[dict]:
    """Fetch and normalize metadata for every track referenced by the URL."""
    kind, sid = parse_spotify_url(url)
    sp = _client()
    genre_cache: dict = {}
    tracks: List[dict] = []

    if kind == "track":
        track = sp.track(sid)
        album = track["album"]
        tracks.append(_track_from_full(sp, track, album, genre_cache))

    elif kind == "album":
        album = sp.album(sid)
        results = album["tracks"]
        items = results["items"]
        while results.get("next"):
            results = sp.next(results)
            items.extend(results["items"])
        for item in items:
            # album track objects are simplified; they lack album ref
            tracks.append(_track_from_full(sp, item, album, genre_cache))

    elif kind == "playlist":
        results = sp.playlist_items(sid, additional_types=("track",))
        items = results["items"]
        while results.get("next"):
            results = sp.next(results)
            items.extend(results["items"])
        for item in items:
            track = item.get("track")
            if not track or track.get("type") != "track":
                continue
            album = track.get("album") or {}
            tracks.append(_track_from_full(sp, track, album, genre_cache))

    return tracks
