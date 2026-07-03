"""
AutoCut — FastAPI server
트랙 C (Windows): WebRTC VAD + faster-whisper ASR
"""
import asyncio
import glob
import json
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from vad import detect_speech, extract_all_flags, _decode_audio_16k
from draft import build_draft
from youtube import download_youtube, heatmap_peaks
from highlight import analyze_highlights
from highlight import save_key, clear_key, key_status

# ── ASR lock: faster-whisper / numba은 동시 호출 시 segfault ──
_asr_lock = asyncio.Lock()
_asr_model = None

UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# job_id → {"path": Path, "suffix": str, "heatmap": list|None, "total": float}
JOBS: dict[str, dict] = {}

FILLER_KO = {
    "어", "음", "에", "아", "그", "저", "뭐", "이제", "근데", "그냥",
    "그래서", "막", "좀", "약간", "진짜", "아무튼", "하여튼", "어쨌든",
}

app = FastAPI(title="AutoCut")
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def index():
    return (Path(__file__).parent / "static" / "index.html").read_text(encoding="utf-8")


def _get_video_wh(path: str) -> tuple[int, int]:
    try:
        import av
        c = av.open(path)
        vs = next((s for s in c.streams if s.type == "video"), None)
        if vs:
            w, h = vs.width, vs.height
            c.close()
            return w, h
        c.close()
    except Exception:
        pass
    return 1080, 1920


def _get_asr_model():
    global _asr_model
    if _asr_model is None:
        from faster_whisper import WhisperModel
        _asr_model = WhisperModel("medium", device="cpu", compute_type="int8")
    return _asr_model


def _run_asr(audio_path: str) -> tuple[list[dict], list[dict]]:
    model = _get_asr_model()
    seg_gen, _ = model.transcribe(
        audio_path, language="ko", vad_filter=True, word_timestamps=True,
    )
    segments, words = [], []
    for seg in seg_gen:
        segments.append({"text": seg.text.strip(), "start": seg.start, "end": seg.end})
        if seg.words:
            for w in seg.words:
                words.append({"word": w.word, "start": w.start, "end": w.end})
    return segments, words


def _snap_to_word_boundaries(
    keep_ranges: list[tuple[float, float]],
    words: list[dict],
    tolerance: float = 0.25,
) -> list[tuple[float, float]]:
    """Snap keep_range edges to the nearest word start/end.

    Prevents mid-word cuts by aligning boundaries to ASR word timestamps.
    tolerance: max seconds a boundary may shift to reach a word edge.
    """
    if not words:
        return keep_ranges

    w_starts = [w["start"] for w in words]
    w_ends   = [w["end"]   for w in words]

    snapped = []
    for ks, ke in keep_ranges:
        # Snap start → nearest word start within tolerance
        new_ks = ks
        best = float("inf")
        for ws in w_starts:
            d = abs(ws - ks)
            if d < best and d <= tolerance:
                best, new_ks = d, ws

        # Snap end → nearest word end within tolerance
        new_ke = ke
        best = float("inf")
        for we in w_ends:
            d = abs(we - ke)
            if d < best and d <= tolerance:
                best, new_ke = d, we

        if new_ke > new_ks + 0.05:
            snapped.append((new_ks, new_ke))

    if not snapped:
        return keep_ranges

    # Re-merge after snapping (boundaries may now overlap)
    snapped.sort()
    merged = [list(snapped[0])]
    for s, e in snapped[1:]:
        if s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    return [(s, e) for s, e in merged]


def _run_asr_array(audio_np) -> list[dict]:
    """Transcribe an in-memory 16kHz float32 mono array (clip-relative times)."""
    model = _get_asr_model()
    seg_gen, _ = model.transcribe(
        audio_np, language="ko", vad_filter=True,
    )
    return [{"text": s.text.strip(), "start": s.start, "end": s.end} for s in seg_gen]


def _probe_duration(path: str) -> float:
    try:
        import av
        c = av.open(path)
        d = 0.0
        if c.duration:
            d = c.duration / 1_000_000
        else:
            vs = next((s for s in c.streams if s.type == "video"), None)
            if vs and vs.duration and vs.time_base:
                d = float(vs.duration * vs.time_base)
        c.close()
        return d
    except Exception:
        return 0.0


def _is_filler(text: str) -> bool:
    return text.strip().rstrip(".") in FILLER_KO


def _make_srt(segments: list[dict]) -> str:
    def tc(s: float) -> str:
        h, r = divmod(s, 3600); m, r = divmod(r, 60)
        return f"{int(h):02d}:{int(m):02d}:{int(r):02d},{int((s%1)*1000):03d}"
    lines = []
    for i, seg in enumerate(segments, 1):
        lines += [str(i), f"{tc(seg['start'])} --> {tc(seg['end'])}", seg["text"], ""]
    return "\n".join(lines)


def _original_to_edit(orig_t: float, keep_ranges: list) -> float | None:
    """Map an original-video timestamp to the edited (cut) timeline.

    Returns None if the timestamp falls inside a removed (cut-out) region.
    """
    edit_cursor = 0.0
    for src_start, src_end in keep_ranges:
        dur = src_end - src_start
        if src_start <= orig_t <= src_end:
            return edit_cursor + (orig_t - src_start)
        edit_cursor += dur
    return None


def _remap_subtitles_to_edit(subtitles: list, keep_ranges: list) -> list:
    """Convert subtitle times from original video to edited timeline.

    Subtitles entirely inside cut-out regions are dropped; partially
    overlapping ones are clamped to the nearest kept boundary.
    """
    out = []
    for sub in subtitles:
        es = _original_to_edit(sub["start"], keep_ranges)
        ee = _original_to_edit(sub["end"],   keep_ranges)
        # clamp endpoints that landed in a removed region
        if es is None:
            es = _original_to_edit(sub["start"] + 0.05, keep_ranges)
        if ee is None:
            ee = _original_to_edit(sub["end"] - 0.05, keep_ranges)
        if es is None or ee is None or ee - es < 0.05:
            continue
        out.append({"text": sub["text"], "start": es, "end": ee})
    return out


def _subtract_ranges(keep: list, cuts: list) -> list:
    result = []
    for ks, ke in keep:
        current = [(ks, ke)]
        for cs, ce in cuts:
            nxt = []
            for s, e in current:
                if ce <= s or cs >= e:
                    nxt.append((s, e))
                else:
                    if s < cs: nxt.append((s, cs))
                    if ce < e: nxt.append((ce, e))
            current = nxt
        result.extend(current)
    return [(s, e) for s, e in result if e - s > 0.05]


async def _process(
    video_path: Path,
    aggressiveness: int   = 2,
    pad_before_ms: int    = 150,
    pad_after_ms: int     = 150,
    min_silence_ms: int   = 400,
) -> AsyncGenerator[str, None]:
    def sse(event: str, data: dict) -> str:
        return f"data: {json.dumps({'event': event, **data}, ensure_ascii=False)}\n\n"

    await asyncio.sleep(0.1)

    # ── Step 1: VAD ──
    yield sse("step", {"step": "silence", "label": "음성 구간 감지 중 (VAD)…"})
    await asyncio.sleep(0.5)
    try:
        loop = asyncio.get_event_loop()
        total, keep = await loop.run_in_executor(
            None, detect_speech,
            str(video_path),
            aggressiveness,
            pad_before_ms / 1000.0,
            pad_after_ms  / 1000.0,
            min_silence_ms / 1000.0,
        )
    except Exception as e:
        yield sse("error", {"message": f"VAD 실패: {e}"}); return

    if not keep:
        yield sse("error", {"message": "음성 구간을 찾지 못했습니다. VAD 민감도를 낮추거나 여유 시간을 늘려보세요."}); return

    removed = total - sum(e - s for s, e in keep)
    yield sse("silence_done", {
        "total": round(total, 2),
        "keep_count": len(keep),
        "removed_sec": round(removed, 2),
    })
    await asyncio.sleep(0.5)

    # ── Step 2: ASR ──
    yield sse("step", {"step": "asr", "label": "음성 인식 중… (첫 실행 시 모델 다운로드)"})
    await asyncio.sleep(0.5)
    segments, words = [], []
    try:
        async with _asr_lock:
            loop = asyncio.get_event_loop()
            segments, words = await loop.run_in_executor(None, _run_asr, str(video_path))
    except Exception as e:
        yield sse("error", {"message": f"ASR 실패: {e}"}); return

    yield sse("asr_done", {
        "segment_count": len(segments),
        "text_preview": " ".join(s["text"] for s in segments)[:120],
    })
    await asyncio.sleep(0.5)

    # ── Step 3: Filler + word-boundary snap ──
    yield sse("step", {"step": "filler", "label": "잔말·NG 컷 + 단어 경계 정렬 중…"})
    await asyncio.sleep(0.5)
    filler_segs  = [s for s in segments if _is_filler(s["text"])]
    keep_trimmed = _subtract_ranges(keep, [(s["start"], s["end"]) for s in filler_segs])
    keep_final   = _snap_to_word_boundaries(keep_trimmed, words, tolerance=0.25)
    yield sse("filler_done", {
        "filler_count": len(filler_segs),
        "final_keep":   len(keep_final),
    })
    await asyncio.sleep(0.5)

    # ── Step 4: Draft ──
    yield sse("step", {"step": "draft", "label": "캡컷 드래프트 생성 중…"})
    await asyncio.sleep(0.5)
    w, h = _get_video_wh(str(video_path))
    draft_name = f"autocut_{video_path.stem}_{int(time.time())}"
    subtitles  = [s for s in segments if not _is_filler(s["text"])]
    try:
        loop = asyncio.get_event_loop()
        draft_dir = await loop.run_in_executor(
            None, build_draft,
            str(video_path.resolve()), keep_final, total, draft_name, subtitles, w, h,
        )
    except Exception as e:
        yield sse("error", {"message": f"드래프트 생성 실패: {e}"}); return

    # SRT is aligned to the EDITED (cut) timeline so it matches the exported video.
    edit_subtitles = _remap_subtitles_to_edit(subtitles, keep_final)
    srt_path = video_path.with_suffix(".srt")
    srt_path.write_text(_make_srt(edit_subtitles), encoding="utf-8")

    final_dur = sum(e - s for s, e in keep_final)
    yield sse("done", {
        "draft_name":     draft_name,
        "draft_path":     str(draft_dir),
        "srt_id":         video_path.stem,
        "original_sec":   round(total, 1),
        "final_sec":      round(final_dur, 1),
        "cuts":           len(keep_final),
        "subtitle_count": len(subtitles),
        "transcript": [
            {"text": s["text"], "start": round(s["start"], 2), "end": round(s["end"], 2)}
            for s in segments
        ],
    })


def _snap_quiet(samples, sr: int, t: float, window: float = 0.25) -> float:
    """Nudge a cut point to the quietest spot within ±window (cleaner cuts)."""
    if samples is None or len(samples) == 0:
        return t
    lo = max(0, int((t - window) * sr))
    hi = min(len(samples), int((t + window) * sr))
    if hi - lo < sr // 50:
        return t
    seg = samples[lo:hi]
    frame = max(1, sr // 100)               # 10ms frames
    best_i, best_e = 0, float("inf")
    for i in range(0, len(seg) - frame, frame):
        e = float((seg[i:i+frame] ** 2).mean())
        if e < best_e:
            best_e, best_i = e, i
    return (lo + best_i + frame / 2) / sr


async def _process_highlight(
    video_path: Path,
    job_id: str,
    n_clips: int,
    max_sec: int,
    total: float,
    heatmap: list | None,
    montage: bool = True,
) -> AsyncGenerator[str, None]:
    def sse(event: str, data: dict) -> str:
        return f"data: {json.dumps({'event': event, **data}, ensure_ascii=False)}\n\n"

    loop = asyncio.get_event_loop()
    await asyncio.sleep(0.1)

    # ── Step 1: Gemini highlight analysis ──
    label = "Gemini가 영상을 분석하는 중… (몽타주)" if montage else "Gemini가 영상을 분석하는 중…"
    yield sse("step", {"step": "highlight", "label": label})
    await asyncio.sleep(0.3)
    peaks = heatmap_peaks(heatmap, 8)
    try:
        clips = await loop.run_in_executor(
            None,
            lambda: analyze_highlights(str(video_path), n_clips, max_sec, peaks, "한국어", montage, total),
        )
    except Exception as e:
        yield sse("error", {"message": f"Gemini 분석 실패: {e}"}); return

    if not clips:
        yield sse("error", {"message": "하이라이트 구간을 찾지 못했습니다."}); return

    yield sse("highlight_done", {
        "clip_count": len(clips),
        "used_heatmap": bool(peaks),
    })
    await asyncio.sleep(0.3)

    # ── Step 2: decode audio once (for per-segment subtitles + cut snapping) ──
    yield sse("step", {"step": "asr", "label": "각 클립 자막 생성 중…"})
    await asyncio.sleep(0.3)
    try:
        samples, _ = await loop.run_in_executor(None, _decode_audio_16k, str(video_path))
    except Exception:
        samples = None

    # ── Step 3: build N vertical drafts (each may stitch multiple segments) ──
    yield sse("step", {"step": "draft", "label": "세로(9:16) 드래프트 생성 중… (원본 비율 유지)"})
    await asyncio.sleep(0.3)
    w, h = _get_video_wh(str(video_path))
    SR = 16000

    # Reliable duration: decoded audio length beats an unreliable container probe.
    if samples is not None and len(samples):
        audio_total = len(samples) / SR
        if not total or total < 1 or total > audio_total * 1.5:
            total = audio_total

    print(f"[highlight] clips={len(clips)} total={total:.1f}s "
          f"durations={[round(c['duration'],1) for c in clips]}")
    results = []

    for i, clip in enumerate(clips, 1):
        # clamp + snap each segment to a quiet boundary for cleaner cuts
        keep_ranges = []
        for a, b in clip["segments"]:
            a = max(0.0, float(a))
            b = float(b)
            if total and total > 2:          # clamp to video end only if total is sane
                b = min(b, total)
            if b - a < 0.4:                  # skip degenerate segment
                continue
            # snap to nearby quiet point, but never let it shrink the segment much
            sa = _snap_quiet(samples, SR, a)
            sb = _snap_quiet(samples, SR, b)
            if sb - sa >= max(0.4, 0.6 * (b - a)):
                a, b = sa, sb
            keep_ranges.append((round(a, 3), round(b, 3)))

        print(f"[highlight] clip {i}: segments={clip['segments']} -> keep={keep_ranges}")
        if not keep_ranges:
            continue

        # per-segment subtitles → original-video time (build_draft remaps them)
        draft_subs = []
        if samples is not None and len(samples):
            for (a, b) in keep_ranges:
                chunk = samples[int(a * SR): int(b * SR)]
                if len(chunk) <= SR // 2:
                    continue
                try:
                    async with _asr_lock:
                        segs = await loop.run_in_executor(None, _run_asr_array, chunk)
                except Exception:
                    segs = []
                for s in segs:
                    draft_subs.append({"text": s["text"], "start": s["start"] + a, "end": s["end"] + a})

        draft_name = f"autocut_hl_{video_path.stem}_{i}_{int(time.time())}"
        try:
            draft_dir = await loop.run_in_executor(
                None, build_draft,
                str(video_path.resolve()), keep_ranges, total, draft_name,
                draft_subs, w, h, True,   # vertical=True (original ratio preserved)
            )
        except Exception as e:
            yield sse("error", {"message": f"클립 {i} 드래프트 생성 실패: {e}"}); return

        # per-clip SRT on the stitched (edit) timeline
        srt_id = f"{job_id}_clip{i}"
        edit_subs = _remap_subtitles_to_edit(draft_subs, keep_ranges)
        (UPLOAD_DIR / f"{srt_id}.srt").write_text(_make_srt(edit_subs), encoding="utf-8")

        clip_dur = sum(b - a for a, b in keep_ranges)
        results.append({
            "index":      i,
            "title":      clip["title"] or f"하이라이트 {i}",
            "reason":     clip["reason"],
            "score":      round(clip["score"], 2),
            "start":      round(keep_ranges[0][0], 1),
            "end":        round(keep_ranges[-1][1], 1),
            "duration":   round(clip_dur, 1),
            "seg_count":  len(keep_ranges),
            "draft_name": draft_name,
            "draft_path": str(draft_dir),
            "srt_id":     srt_id,
            "sub_count":  len(edit_subs),
        })
        yield sse("clip_done", {"index": i, "total": len(clips)})

    if not results:
        yield sse("error", {"message": "유효한 클립을 만들지 못했습니다."}); return

    yield sse("highlight_result", {
        "original_sec": round(total, 1),
        "clips": results,
    })


# ── Endpoints ───────────────────────────────────────────────────────────────

@app.post("/analyze")
async def analyze(
    mode: str = Form("silence"),
    url:  str = Form(""),
    file: UploadFile | None = File(None),
):
    job_id = uuid.uuid4().hex[:8]
    loop = asyncio.get_event_loop()
    heatmap = None
    title   = ""

    # ── Source: YouTube URL or uploaded file ──
    if url.strip():
        try:
            info = await loop.run_in_executor(
                None, download_youtube, url.strip(), UPLOAD_DIR, job_id
            )
        except Exception as e:
            return {"error": f"유튜브 다운로드 실패: {e}"}
        save_path = info["path"]
        suffix    = info["suffix"]
        heatmap   = info["heatmap"]
        title     = info.get("title", "")
        total     = info["duration"] or _probe_duration(str(save_path))
    elif file is not None:
        suffix = Path(file.filename).suffix.lower()
        if suffix not in {".mp4", ".mov", ".m4v", ".avi", ".mkv"}:
            return {"error": "지원하지 않는 형식"}
        save_path = UPLOAD_DIR / f"{job_id}{suffix}"
        save_path.write_bytes(await file.read())
        title = Path(file.filename).name
        total = 0.0
    else:
        return {"error": "파일 또는 유튜브 URL이 필요합니다."}

    JOBS[job_id] = {
        "path": save_path, "suffix": suffix, "heatmap": heatmap,
        "total": total, "title": title,
    }

    # ── Silence mode: precompute VAD flags for live slider preview ──
    if mode == "silence":
        flags_dict, dt, total = await loop.run_in_executor(
            None, extract_all_flags, str(save_path)
        )
        JOBS[job_id]["total"] = total
        return {
            "job_id":    job_id,
            "suffix":    suffix,
            "title":     title,
            "total_sec": round(total, 3),
            "dt":        dt,
            "flags":     flags_dict,
        }

    # ── Highlight mode: just confirm source is ready ──
    if not total:
        total = _probe_duration(str(save_path))
        JOBS[job_id]["total"] = total
    return {
        "job_id":           job_id,
        "suffix":           suffix,
        "title":            title,
        "total_sec":        round(total, 3),
        "mode":             "highlight",
        "heatmap_available": bool(heatmap),
    }


@app.post("/process")
async def process(
    job_id:         str = Form(...),
    suffix:         str = Form(""),
    aggressiveness: int = Form(2),
    pad_before_ms:  int = Form(150),
    pad_after_ms:   int = Form(150),
    min_silence_ms: int = Form(400),
):
    # Prefer the JOBS registry (handles non-.mp4 YouTube downloads); fall back
    # to job_id+suffix for older clients.
    job = JOBS.get(job_id)
    save_path = Path(job["path"]) if job else (UPLOAD_DIR / f"{job_id}{suffix}")
    if not save_path.exists():
        return {"error": "파일 없음 — 다시 업로드해주세요"}

    async def stream():
        async for chunk in _process(
            save_path, aggressiveness, pad_before_ms, pad_after_ms, min_silence_ms
        ):
            yield chunk

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.post("/process-highlight")
async def process_highlight(
    job_id:  str = Form(...),
    n_clips: int = Form(3),
    max_sec: int = Form(60),
    montage: int = Form(1),
):
    job = JOBS.get(job_id)
    if not job or not Path(job["path"]).exists():
        return {"error": "파일 없음 — 다시 불러와주세요"}

    n_clips = max(1, min(5, n_clips))
    save_path = Path(job["path"])
    total     = job.get("total") or _probe_duration(str(save_path))
    heatmap   = job.get("heatmap")

    async def stream():
        async for chunk in _process_highlight(
            save_path, job_id, n_clips, max_sec, total, heatmap, bool(montage),
        ):
            yield chunk

    return StreamingResponse(stream(), media_type="text/event-stream")


def _find_capcut_exe() -> Path | None:
    if sys.platform == "darwin":
        for c in [Path("/Applications/CapCut.app"),
                  Path.home() / "Applications/CapCut.app"]:
            if c.exists():
                return c
        return None
    # Windows
    base = Path.home() / "AppData/Local/CapCut/Apps"
    versioned = sorted(glob.glob(str(base / "*" / "CapCut.exe")), reverse=True)
    if versioned:
        return Path(versioned[0])
    root = base / "CapCut.exe"
    return root if root.exists() else None


@app.post("/open-capcut")
async def open_capcut():
    exe = _find_capcut_exe()
    if exe is None:
        return {"error": "CapCut 실행 파일을 찾을 수 없습니다."}
    try:
        if sys.platform == "darwin":
            # launch the .app bundle detached
            subprocess.Popen(["open", str(exe)])
        else:
            subprocess.Popen([str(exe)], creationflags=subprocess.DETACHED_PROCESS)
        return {"ok": True, "exe": str(exe)}
    except Exception as e:
        return {"error": str(e)}


@app.get("/gemini-key")
async def gemini_key_get():
    return key_status()


@app.post("/gemini-key")
async def gemini_key_set(key: str = Form(...)):
    k = key.strip()
    if len(k) < 10:
        return {"error": "유효하지 않은 키 형식입니다."}
    try:
        save_key(k)
    except Exception as e:
        return {"error": f"저장 실패: {e}"}
    return {"ok": True, **key_status()}


@app.delete("/gemini-key")
async def gemini_key_delete():
    clear_key()
    return {"ok": True, **key_status()}


@app.get("/download/srt/{srt_id}")
async def download_srt(srt_id: str):
    srt_path = UPLOAD_DIR / f"{srt_id}.srt"
    if not srt_path.exists():
        return {"error": "SRT 파일 없음"}
    return FileResponse(
        path=srt_path,
        media_type="text/plain; charset=utf-8",
        filename=f"{srt_id}.srt",
        headers={"Content-Disposition": f'attachment; filename="{srt_id}.srt"'},
    )
