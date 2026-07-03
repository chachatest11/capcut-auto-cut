"""
Subject-tracking crop for 9:16 vertical output.

Detects the main face in the selected segments and computes a per-segment
horizontal offset so the speaker stays centered in the vertical frame —
without re-encoding the video. The offset is expressed as a CapCut
`clip.transform.x` value (normalized: 1.0 == half the canvas width).

Each input segment is split into short windows; windows with a similar
offset are merged, so the crop holds still when the subject is still and
recenters when they move (approximates a follow-cam using only static
transforms, which CapCut renders reliably).
"""
import cv2
import numpy as np

# Must match the vertical canvas in draft.py
CANVAS_W = 1080
CANVAS_H = 1920

WINDOW_SEC   = 2.5     # recenter granularity
SAMPLE_FPS   = 3.0     # face samples per second
MERGE_THRESH = 0.08    # merge adjacent windows whose offset differs less than this

_cascade = None


def _get_cascade():
    global _cascade
    if _cascade is None:
        _cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
    return _cascade


def _fraction_to_offset(frac: float, src_w: int, src_h: int) -> float:
    """Map a face center (0..1 across source width) to clip.transform.x."""
    if src_h <= 0:
        return 0.0
    rendered_w = CANVAS_H * (src_w / src_h)      # source scaled to fill canvas height
    if rendered_w <= CANVAS_W:                   # source not wider than 9:16 → no h-crop
        return 0.0
    # shift needed (px, canvas space) to bring face to canvas center; +x = move right
    shift_px = -(frac - 0.5) * rendered_w
    norm = shift_px / (CANVAS_W / 2)             # CapCut unit: 1.0 == half canvas width
    max_norm = ((rendered_w - CANVAS_W) / 2) / (CANVAS_W / 2)   # keep frame covered
    return round(max(-max_norm, min(max_norm, norm)), 4)


def _median_face_fraction(cap, t0: float, t1: float) -> float | None:
    """Median horizontal face position over [t0, t1); None if no faces seen."""
    cascade = _get_cascade()
    fracs = []
    step = 1.0 / SAMPLE_FPS
    t = t0
    while t < t1:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000.0)
        ok, frame = cap.read()
        if not ok:
            break
        h, w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = cascade.detectMultiScale(
            gray, scaleFactor=1.2, minNeighbors=5,
            minSize=(max(24, int(w * 0.04)), max(24, int(w * 0.04))),
        )
        if len(faces):
            x, y, fw, fh = max(faces, key=lambda r: r[2] * r[3])  # largest = main subject
            fracs.append((x + fw / 2) / w)
        t += step
    if not fracs:
        return None
    return float(np.median(fracs))


def track_segments(
    video_path: str,
    ranges: list[tuple[float, float]],
    src_w: int,
    src_h: int,
) -> tuple[list[tuple[float, float]], list[float]]:
    """For each input range, return expanded sub-ranges + matching x-offsets.

    Falls back to the original ranges with 0.0 offset on any failure.
    """
    fallback = (list(ranges), [0.0] * len(ranges))
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return fallback
    except Exception:
        return fallback

    out_ranges: list[tuple[float, float]] = []
    out_offsets: list[float] = []
    try:
        for (a, b) in ranges:
            # build windows for this range
            windows = []
            t = a
            while t < b - 0.05:
                w_end = min(b, t + WINDOW_SEC)
                frac = _median_face_fraction(cap, t, w_end)
                off = _fraction_to_offset(frac, src_w, src_h) if frac is not None else None
                windows.append([t, w_end, off])
                t = w_end

            if not windows:
                out_ranges.append((a, b)); out_offsets.append(0.0); continue

            # fill windows with no face using nearest known offset
            known = [w[2] for w in windows if w[2] is not None]
            default_off = float(np.median(known)) if known else 0.0
            for w in windows:
                if w[2] is None:
                    w[2] = default_off

            # merge adjacent windows with similar offset
            merged = [windows[0][:]]
            for s, e, off in windows[1:]:
                if abs(off - merged[-1][2]) < MERGE_THRESH:
                    merged[-1][1] = e   # extend, keep first offset
                else:
                    merged.append([s, e, off])

            for s, e, off in merged:
                out_ranges.append((round(s, 3), round(e, 3)))
                out_offsets.append(round(off, 4))
    finally:
        cap.release()

    if not out_ranges:
        return fallback
    return out_ranges, out_offsets
