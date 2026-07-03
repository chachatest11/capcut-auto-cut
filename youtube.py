"""
YouTube source: download a video (progressive, no ffmpeg needed) and
extract the "most replayed" heatmap when available.

yt-dlp exposes a `heatmap` field in the info dict for videos that have
the most-replayed graph enabled:
    [{"start_time": float, "end_time": float, "value": 0.0..1.0}, ...]
Higher value = more viewer replays = likely a highlight.
"""
from pathlib import Path

import yt_dlp


def download_youtube(url: str, out_dir: Path, job_id: str) -> dict:
    """Download a YouTube video to out_dir/<job_id>.<ext>.

    Returns dict: {path, suffix, title, duration, heatmap}
    heatmap is a list of {start, end, value} or None.

    Uses progressive formats (single file with audio+video) so no ffmpeg
    merge step is required.
    """
    outtmpl = str(out_dir / f"{job_id}.%(ext)s")
    opts = {
        # progressive mp4 (has both audio+video in one stream) → no ffmpeg merge
        "format": "best[ext=mp4][acodec!=none][vcodec!=none]/best[acodec!=none][vcodec!=none]/best",
        "outtmpl": outtmpl,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        # the actually written file
        path = Path(ydl.prepare_filename(info))

    # heatmap → normalized list
    heatmap = None
    raw = info.get("heatmap")
    if raw:
        heatmap = [
            {
                "start": round(float(h["start_time"]), 2),
                "end":   round(float(h["end_time"]), 2),
                "value": round(float(h["value"]), 4),
            }
            for h in raw
        ]

    return {
        "path":     path,
        "suffix":   path.suffix.lower(),
        "title":    info.get("title", ""),
        "duration": float(info.get("duration") or 0.0),
        "heatmap":  heatmap,
    }


def heatmap_peaks(heatmap: list[dict] | None, top_n: int = 8) -> list[dict]:
    """Return the top-N highest-intensity heatmap windows, sorted by time."""
    if not heatmap:
        return []
    ranked = sorted(heatmap, key=lambda h: h["value"], reverse=True)[:top_n]
    return sorted(ranked, key=lambda h: h["start"])
