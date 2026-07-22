"""FastAPI application for 432 Converter.

Holds all job state in memory, runs conversions on a background thread pool,
and streams per-track progress over a WebSocket. No database.
"""
import asyncio
import os
import subprocess
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, List

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import config
import converter
import spotify

app = FastAPI(title="432 Converter")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# In-memory state
# ---------------------------------------------------------------------------
JOBS: Dict[str, dict] = {}
JOBS_LOCK = threading.Lock()
EXECUTOR = ThreadPoolExecutor(max_workers=2)

# The event loop is captured at startup so worker threads can push WS events.
MAIN_LOOP: asyncio.AbstractEventLoop = None


class WSManager:
    def __init__(self):
        self.active: List[WebSocket] = []
        self.lock = asyncio.Lock()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        async with self.lock:
            self.active.append(ws)

    async def disconnect(self, ws: WebSocket):
        async with self.lock:
            if ws in self.active:
                self.active.remove(ws)

    async def broadcast(self, message: dict):
        async with self.lock:
            targets = list(self.active)
        for ws in targets:
            try:
                await ws.send_json(message)
            except Exception:
                await self.disconnect(ws)


ws_manager = WSManager()


def push_event(message: dict):
    """Thread-safe broadcast onto the asyncio loop from a worker thread."""
    if MAIN_LOOP is None:
        return
    try:
        asyncio.run_coroutine_threadsafe(ws_manager.broadcast(message), MAIN_LOOP)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------
class ConvertRequest(BaseModel):
    url: str


class ConfigRequest(BaseModel):
    SPOTIFY_CLIENT_ID: str = None
    SPOTIFY_CLIENT_SECRET: str = None
    output_dir: str = None
    delay_between_tracks: float = None


# ---------------------------------------------------------------------------
# Job helpers
# ---------------------------------------------------------------------------
def _new_track_state(meta: dict) -> dict:
    return {
        "title": meta.get("title", ""),
        "artist": meta.get("artist", ""),
        "album": meta.get("album", ""),
        "album_artist": meta.get("album_artist", ""),
        "track_number": meta.get("track_number", 0),
        "cover_url": meta.get("cover_url", ""),
        "year": meta.get("year", ""),
        "status": "queued",
        "error": "",
        "yt_title": "",
        "warning": "",
        "output_path": "",
        "meta": meta,
    }


def _update_track(job_id: str, idx: int, **fields):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            return
        track = job["tracks"][idx]
        track.update(fields)
        snapshot = {k: v for k, v in track.items() if k != "meta"}
    push_event({
        "type": "track_update",
        "job_id": job_id,
        "track_index": idx,
        "track": snapshot,
    })


def _status_cb_for(job_id: str, idx: int):
    def cb(stage: str, extra: dict):
        fields = {}
        if stage == "warning":
            fields["warning"] = f"YouTube title may not match: {extra.get('yt_title', '')}"
            fields["yt_title"] = extra.get("yt_title", "")
        elif stage == "error":
            fields["status"] = "error"
            fields["error"] = extra.get("error", "")
        elif stage == "done":
            fields["status"] = "done"
            fields["output_path"] = extra.get("output_path", "")
        else:
            fields["status"] = stage
        _update_track(job_id, idx, **fields)
    return cb


def _process_track(job_id: str, idx: int, query_override: str = None):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            return
        meta = job["tracks"][idx]["meta"]
        output_dir = job["output_dir"]
    cb = _status_cb_for(job_id, idx)
    result = converter.convert_track(meta, output_dir, cb, query_override=query_override)
    return result


def _run_job(job_id: str):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            return
        n = len(job["tracks"])
        delay = job["delay"]
    for idx in range(n):
        with JOBS_LOCK:
            job = JOBS.get(job_id)
            if not job:
                return
            status = job["tracks"][idx]["status"]
        if status == "done":
            continue
        _process_track(job_id, idx)
        if idx < n - 1 and delay > 0:
            time.sleep(delay)
    push_event({"type": "job_done", "job_id": job_id})


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.on_event("startup")
async def _startup():
    global MAIN_LOOP
    MAIN_LOOP = asyncio.get_event_loop()


@app.get("/api/config")
def get_config():
    cfg = config.load_config()
    return {**cfg, "configured": config.is_configured()}


@app.post("/api/config")
def post_config(req: ConfigRequest):
    values = {k: v for k, v in req.dict().items() if v is not None}
    cfg = config.save_config(values)
    return {**cfg, "configured": config.is_configured()}


@app.post("/api/convert")
def convert(req: ConvertRequest):
    if not config.is_configured():
        raise HTTPException(status_code=400, detail="Spotify credentials not configured.")
    try:
        tracks = spotify.fetch_tracks(req.url)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc))
    if not tracks:
        raise HTTPException(status_code=400, detail="No tracks found for that URL.")

    cfg = config.load_config()
    job_id = uuid.uuid4().hex[:12]
    job = {
        "job_id": job_id,
        "url": req.url,
        "created_at": time.time(),
        "output_dir": cfg["output_dir"],
        "delay": float(cfg.get("delay_between_tracks", 0) or 0),
        "tracks": [_new_track_state(m) for m in tracks],
    }
    with JOBS_LOCK:
        JOBS[job_id] = job

    EXECUTOR.submit(_run_job, job_id)
    push_event({"type": "job_created", "job_id": job_id})
    return {"job_id": job_id, "track_count": len(tracks)}


def _job_snapshot(job: dict) -> dict:
    return {
        "job_id": job["job_id"],
        "url": job["url"],
        "created_at": job["created_at"],
        "output_dir": job["output_dir"],
        "tracks": [{k: v for k, v in t.items() if k != "meta"} for t in job["tracks"]],
    }


@app.get("/api/status/{job_id}")
def status(job_id: str):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found.")
        return _job_snapshot(job)


@app.get("/api/jobs")
def jobs():
    with JOBS_LOCK:
        return [_job_snapshot(j) for j in sorted(JOBS.values(), key=lambda x: x["created_at"], reverse=True)]


class RetryRequest(BaseModel):
    query_override: str = None


@app.post("/api/retry/{job_id}/{track_index}")
def retry(job_id: str, track_index: int, req: RetryRequest = None):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found.")
        if track_index < 0 or track_index >= len(job["tracks"]):
            raise HTTPException(status_code=404, detail="Track not found.")
        job["tracks"][track_index]["status"] = "queued"
        job["tracks"][track_index]["error"] = ""
        job["tracks"][track_index]["warning"] = ""

    query_override = req.query_override if req else None
    EXECUTOR.submit(_process_track, job_id, track_index, query_override)
    return {"ok": True}


@app.get("/api/stats")
def stats():
    """Aggregate converted-track count and total output size."""
    cfg = config.load_config()
    out_dir = Path(cfg["output_dir"])
    count = 0
    total_bytes = 0
    if out_dir.exists():
        for p in out_dir.rglob("*.mp3"):
            try:
                total_bytes += p.stat().st_size
                count += 1
            except OSError:
                pass
    return {
        "count": count,
        "size_gb": round(total_bytes / (1024 ** 3), 2),
        "output_dir": str(out_dir),
    }


class RevealRequest(BaseModel):
    path: str


@app.post("/api/reveal")
def reveal(req: RevealRequest):
    """Open the containing folder in Finder/Explorer."""
    path = req.path
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found.")
    try:
        if sys.platform == "darwin":
            subprocess.run(["open", "-R", path])
        elif sys.platform.startswith("win"):
            subprocess.run(["explorer", "/select,", os.path.normpath(path)])
        else:
            subprocess.run(["xdg-open", os.path.dirname(path)])
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc))
    return {"ok": True}


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws_manager.connect(ws)
    try:
        # Send current jobs on connect
        with JOBS_LOCK:
            snapshot = [_job_snapshot(j) for j in JOBS.values()]
        await ws.send_json({"type": "init", "jobs": snapshot})
        while True:
            await ws.receive_text()  # keepalive / ignore inbound
    except WebSocketDisconnect:
        await ws_manager.disconnect(ws)
    except Exception:
        await ws_manager.disconnect(ws)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
