"""
Voice Activity Detection — Silero VAD (neural, speech-only).
Specifically trained to distinguish human speech from music / SFX / noise.
WebRTC VAD was energy-based and could not separate music from voice;
Silero uses a neural model and correctly ignores background music.
"""
import av
import numpy as np
from pathlib import Path

TARGET_SR = 16000
FRAME_MS  = 30                              # resolution of flag array
FRAME_LEN = TARGET_SR * FRAME_MS // 1000   # 480 samples per frame

# Silero threshold per aggressiveness level (0=loose … 3=strict)
# Lower threshold → more frames labelled speech (loose)
# Higher threshold → fewer frames labelled speech (strict)
THRESHOLDS = {0: 0.25, 1: 0.40, 2: 0.55, 3: 0.75}

_silero_model = None


def _get_silero_model():
    global _silero_model
    if _silero_model is None:
        from silero_vad import load_silero_vad
        _silero_model = load_silero_vad()
    return _silero_model


# ── Audio decoding ─────────────────────────────────────────────────────────

def _decode_audio_16k(video_path: str) -> tuple[np.ndarray, float]:
    """Decode any av-supported file → 16 kHz mono float32 + total_sec."""
    container = av.open(video_path)
    audio_stream = next((s for s in container.streams if s.type == "audio"), None)

    if audio_stream is None:
        container.close()
        return np.array([], dtype=np.float32), 0.0

    src_sr = audio_stream.sample_rate
    chunks = []
    for frame in container.decode(audio_stream):
        arr = frame.to_ndarray()
        if arr.ndim > 1:
            arr = arr.mean(axis=0)
        chunks.append(arr.astype(np.float32))
    container.close()

    if not chunks:
        return np.array([], dtype=np.float32), 0.0

    samples = np.concatenate(chunks)
    if np.abs(samples).max() > 1.0:
        samples = samples / 32768.0

    # Normalize peak so VAD receives adequate signal regardless of recording level.
    peak = float(np.abs(samples).max())
    if peak > 1e-6:
        samples = (samples * (0.9 / peak)).astype(np.float32)

    total_sec = len(samples) / src_sr

    if src_sr != TARGET_SR:
        n_out = int(len(samples) * TARGET_SR / src_sr)
        samples = np.interp(
            np.linspace(0, len(samples) - 1, n_out),
            np.arange(len(samples)),
            samples,
        ).astype(np.float32)

    return samples, total_sec


# ── Silero VAD ─────────────────────────────────────────────────────────────

def _run_silero_vad(samples_16k: np.ndarray, threshold: float) -> list[bool]:
    """Run Silero VAD → per-30ms-frame speech flags."""
    import torch
    from silero_vad import get_speech_timestamps

    model = _get_silero_model()
    wav   = torch.from_numpy(samples_16k)

    timestamps = get_speech_timestamps(
        wav, model,
        sampling_rate=TARGET_SR,
        threshold=threshold,
        min_speech_duration_ms=80,
        min_silence_duration_ms=80,
        return_seconds=False,   # returns sample indices
    )

    n_frames = len(samples_16k) // FRAME_LEN
    flags    = [False] * n_frames
    for ts in timestamps:
        s_frame = ts["start"] // FRAME_LEN
        e_frame = (ts["end"] + FRAME_LEN - 1) // FRAME_LEN
        for i in range(max(0, s_frame), min(n_frames, e_frame)):
            flags[i] = True

    return flags


# ── Core algorithm (shared with JS client) ─────────────────────────────────

def _flags_to_keep(
    flags: list[bool | int],
    dt: float,
    total_sec: float,
    pad_before: float,
    pad_after: float,
    min_silence: float,
) -> tuple[float, list[tuple[float, float]]]:
    # 1. Raw speech segments
    speech: list[list[float]] = []
    in_sp = False
    t0 = 0.0
    for i, f in enumerate(flags):
        t = i * dt
        if f and not in_sp:
            t0 = t; in_sp = True
        elif not f and in_sp:
            speech.append([t0, t]); in_sp = False
    if in_sp:
        speech.append([t0, len(flags) * dt])

    if not speech:
        return total_sec, []

    # 2. Merge gaps shorter than min_silence
    merged: list[list[float]] = [speech[0][:]]
    for s, e in speech[1:]:
        if s - merged[-1][1] < min_silence:
            merged[-1][1] = e
        else:
            merged.append([s, e])

    # 3. Apply padding
    padded = [[max(0.0, s - pad_before), min(total_sec, e + pad_after)]
              for s, e in merged]

    # 4. Merge overlapping padded ranges
    keep: list[list[float]] = [padded[0][:]]
    for s, e in padded[1:]:
        if s <= keep[-1][1]:
            keep[-1][1] = max(keep[-1][1], e)
        else:
            keep.append([s, e])

    return total_sec, [(s, e) for s, e in keep]


# ── Public API ──────────────────────────────────────────────────────────────

def extract_all_flags(
    video_path: str,
) -> tuple[dict[str, list[int]], float, float]:
    """
    Decode audio once, run Silero VAD at 4 sensitivity levels.
    Returns (flags_dict, dt_sec, total_sec).
    flags_dict = {"0": [0,1,…], "1": […], "2": […], "3": […]}
    """
    samples, total_sec = _decode_audio_16k(video_path)
    if len(samples) == 0:
        empty = [0]
        return {"0": empty, "1": empty, "2": empty, "3": empty}, FRAME_MS / 1000.0, total_sec

    flags_dict = {}
    for agg, thresh in THRESHOLDS.items():
        raw = _run_silero_vad(samples, thresh)
        flags_dict[str(agg)] = [1 if f else 0 for f in raw]

    return flags_dict, FRAME_MS / 1000.0, total_sec


def detect_speech(
    video_path: str,
    aggressiveness: int    = 2,
    pad_before_sec: float  = 0.15,
    pad_after_sec: float   = 0.15,
    min_silence_sec: float = 0.4,
) -> tuple[float, list[tuple[float, float]]]:
    """
    Returns (total_sec, keep_ranges).
    keep_ranges = speech segments expanded by padding, short gaps merged.
    """
    samples, total_sec = _decode_audio_16k(video_path)
    if len(samples) == 0:
        return total_sec, [(0.0, total_sec)]

    threshold = THRESHOLDS.get(aggressiveness, 0.55)
    flags = _run_silero_vad(samples, threshold)
    return _flags_to_keep(flags, FRAME_MS / 1000.0, total_sec,
                          pad_before_sec, pad_after_sec, min_silence_sec)
