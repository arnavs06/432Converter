"""Configuration storage for 432 Converter.

Config lives at ~/.432converter/config.json and holds Spotify API credentials,
the output directory and the delay between tracks.
"""
import json
import os
from pathlib import Path

CONFIG_DIR = Path.home() / ".432converter"
CONFIG_PATH = CONFIG_DIR / "config.json"
JOBS_PATH = CONFIG_DIR / "jobs.json"

DEFAULT_CONFIG = {
    "SPOTIFY_CLIENT_ID": "",
    "SPOTIFY_CLIENT_SECRET": "",
    "output_dir": str(Path.home() / "Music" / "432hz"),
    "delay_between_tracks": 2.0,
}


def load_config() -> dict:
    """Load config from disk, filling in any missing keys with defaults."""
    cfg = dict(DEFAULT_CONFIG)
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
                stored = json.load(fh)
            if isinstance(stored, dict):
                cfg.update({k: v for k, v in stored.items() if k in DEFAULT_CONFIG})
        except (json.JSONDecodeError, OSError):
            pass
    return cfg


def save_config(new_values: dict) -> dict:
    """Merge new_values into the stored config and persist to disk."""
    cfg = load_config()
    cfg.update({k: v for k, v in new_values.items() if k in DEFAULT_CONFIG})
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=2)
    return cfg


def is_configured() -> bool:
    """True when Spotify credentials are present."""
    cfg = load_config()
    return bool(cfg.get("SPOTIFY_CLIENT_ID")) and bool(cfg.get("SPOTIFY_CLIENT_SECRET"))
