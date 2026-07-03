"""
Silence detection via PyAV + numpy.
Returns list of keep-ranges [(start_sec, end_sec), ...] after removing silent gaps.
"""
import av
import numpy as np
from pathlib import Path


def detect_silence(
    video_path: str,
    silence_db: float = -40.0,
    min_silence_sec: float = 0.4,
    pad_sec: float = 0.08,
) -> tuple[float, list[tuple[float, float]]]:
    """
    Returns (total_duration_sec, keep_ranges).
    keep_ranges: list of (start, end) in seconds to keep.
    """
    path = Path(video_path)
    if not path.exists():
        raise FileNotFoundError(video_path)

    threshold_linear = 10 ** (silence_db / 20.0)

    container = av.open(str(path))
    audio_stream = next((s for s in container.streams if s.type == "audio"), None)
    if audio_stream is None:
        duration = float(container.streams.video[0].duration * container.streams.video[0].time_base)
        container.close()
        return duration, [(0.0, duration)]

    sample_rate = audio_stream.sample_rate
    total_duration = float(container.duration) / 1_000_000.0  # AV duration in microseconds

    # Decode audio into float32 samples
    samples_list = []
    for frame in container.decode(audio_stream):
        arr = frame.to_ndarray()  # shape: (channels, samples) or (samples,)
        if arr.ndim > 1:
            arr = arr.mean(axis=0)
        samples_list.append(arr.astype(np.float32))
    container.close()

    if not samples_list:
        return total_duration, [(0.0, total_duration)]

    samples = np.concatenate(samples_list)
    # Normalize int formats
    if samples.dtype != np.float32 or samples.max() > 1.0:
        max_val = np.iinfo(np.int16).max
        samples = samples / max_val

    # Compute RMS in 20ms windows
    window = int(sample_rate * 0.02)
    n_windows = len(samples) // window
    if n_windows == 0:
        return total_duration, [(0.0, total_duration)]

    trimmed = samples[: n_windows * window].reshape(n_windows, window)
    rms = np.sqrt((trimmed ** 2).mean(axis=1))

    # Mark silent windows
    is_silent = rms < threshold_linear
    dt = 0.02  # seconds per window

    # Build silent segments
    silent_segs: list[tuple[float, float]] = []
    in_silence = False
    seg_start = 0.0
    for i, silent in enumerate(is_silent):
        t = i * dt
        if silent and not in_silence:
            seg_start = t
            in_silence = True
        elif not silent and in_silence:
            if t - seg_start >= min_silence_sec:
                silent_segs.append((seg_start, t))
            in_silence = False
    if in_silence:
        t = n_windows * dt
        if t - seg_start >= min_silence_sec:
            silent_segs.append((seg_start, t))

    # Invert to keep-ranges with padding
    keep: list[tuple[float, float]] = []
    cursor = 0.0
    for s_start, s_end in silent_segs:
        keep_end = max(cursor, s_start - pad_sec)
        if keep_end > cursor + 0.01:
            keep.append((cursor, keep_end))
        cursor = min(total_duration, s_end + pad_sec)
    if cursor < total_duration - 0.01:
        keep.append((cursor, total_duration))

    if not keep:
        keep = [(0.0, total_duration)]

    return total_duration, keep
