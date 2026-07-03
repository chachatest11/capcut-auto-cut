"""
Highlight extraction via Gemini (native video understanding).

Gemini ingests the raw video (visuals + audio) and returns the most
engaging moments as timecoded clips. When a YouTube "most replayed"
heatmap is available it is supplied as extra context so viewer-retention
peaks are prioritised.

Requires a Google Gemini API key. It is read from (in order):
  1. env var  GEMINI_API_KEY
  2. env var  GOOGLE_API_KEY
  3. file     <project>/.gemini_key   (single line)
"""
import json
import os
import time
from pathlib import Path

MODEL = "gemini-2.5-flash"   # native video, cost-effective
_PROJECT = Path(__file__).parent

# Key is stored OUTSIDE the project folder so it is never shared/committed
# by accident. Lives in the user's home config dir.
KEY_DIR  = Path.home() / ".autocut"
KEY_PATH = KEY_DIR / "gemini_key"


def save_key(key: str) -> None:
    KEY_DIR.mkdir(parents=True, exist_ok=True)
    KEY_PATH.write_text(key.strip(), encoding="utf-8")
    try:    # best-effort: restrict permissions (no-op on some Windows setups)
        os.chmod(KEY_PATH, 0o600)
    except Exception:
        pass


def clear_key() -> None:
    try:
        KEY_PATH.unlink()
    except FileNotFoundError:
        pass


def load_key() -> str | None:
    """Return the key from (in order) env vars, stored file, or legacy file."""
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if key:
        return key.strip()
    if KEY_PATH.exists():
        k = KEY_PATH.read_text(encoding="utf-8").strip()
        if k:
            return k
    legacy = _PROJECT / ".gemini_key"        # backward compat
    if legacy.exists():
        k = legacy.read_text(encoding="utf-8").strip()
        if k:
            return k
    return None


def key_status() -> dict:
    """Whether a key is configured, and where it came from (no key exposed)."""
    if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
        return {"set": True, "source": "env"}
    if KEY_PATH.exists() and KEY_PATH.read_text(encoding="utf-8").strip():
        return {"set": True, "source": "file"}
    legacy = _PROJECT / ".gemini_key"
    if legacy.exists() and legacy.read_text(encoding="utf-8").strip():
        return {"set": True, "source": "legacy"}
    return {"set": False, "source": None}


def _get_api_key() -> str:
    key = load_key()
    if not key:
        raise RuntimeError(
            "Gemini API 키가 없습니다. 화면의 ‘Gemini API 키’ 칸에 키를 입력해 저장하거나 "
            "환경변수 GEMINI_API_KEY 를 설정해주세요."
        )
    return key


def _heat_text(heatmap_peaks: list[dict]) -> str:
    if not heatmap_peaks:
        return ""
    rows = "\n".join(
        f"  - {h['start']:.0f}s ~ {h['end']:.0f}s (집중도 {h['value']:.2f})"
        for h in heatmap_peaks
    )
    return (
        "\n\n[유튜브 시청자 '가장 많이 본 부분' — 우선 고려]\n"
        f"{rows}\n"
        "위 구간은 실제 시청자들이 반복 재생한 부분이다. "
        "맥락상 자연스럽다면 이 구간들을 하이라이트에 우선 포함하라."
    )


def _mmss(sec: float) -> str:
    sec = int(round(sec))
    h, r = divmod(sec, 3600)
    m, s = divmod(r, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def _timecode_rule(duration_sec: float) -> str:
    dur = f" 이 영상의 총 길이는 {_mmss(duration_sec)} 이다." if duration_sec else ""
    return (
        f"\n\n[타임코드 규칙 — 매우 중요]{dur}\n"
        '- 모든 start/end 는 반드시 "분:초" 시계 형식의 문자열로 적어라. 예: "0:05", "1:23", "12:07".\n'
        "- 초 단위 소수(예: 12.5)나 정규화 값(0~1), 프레임 번호를 절대 쓰지 마라.\n"
        "- 영상에서 그 장면이 실제로 나오는 정확한 위치를 사용하고, 영상 길이 범위를 벗어나지 마라.\n"
        "- 시간 순서대로 나열하라."
    )


def _build_prompt(n_clips: int, max_sec: int, heatmap_peaks: list[dict],
                  lang_hint: str, montage: bool, duration_sec: float = 0.0) -> str:
    heat_txt = _heat_text(heatmap_peaks)
    tc_rule  = _timecode_rule(duration_sec)

    common = f"""너는 숏폼(쇼츠/릴스) 편집 전문가다. 첨부된 영상을 처음부터 끝까지 직접 보고,
이 영상의 성격(예능/드라마/영화/정보 등)을 스스로 판단한 뒤, 시청자가 가장 재미있어하거나
인상적이라고 느낄 하이라이트 {n_clips}개를 골라라. 무엇이 '하이라이트'인지(웃긴 순간·반전·
감정의 고조·명대사·핵심 정보 등)는 이 영상에 가장 적합하게 네가 판단하라.{heat_txt}{tc_rule}"""

    if montage:
        return common + f"""

[편집 방식 = 몽타주 + 멀티샷 편집]
너는 노련한 편집자다. 각 하이라이트는 여러 개의 짧은 '조각(beat)'을 이어붙인 압축 영상이다.

화자/샷 구성을 적극 활용하라 (영상을 보며 직접 판단):
- 지금 누가 말하는지(화자)를 파악하고, 화자의 핵심 대사와 그에 대한 다른 사람들의
  리액션을 자연스럽게 번갈아 배치하라.
- 여러 명이 함께 나오는 '풀샷'(리액션/분위기가 잘 보이는 장면)을 적절히 섞어 편집 리듬을 만들어라.
- 원본에 이미 존재하는 컷(클로즈업↔풀샷 전환)을 활용해, 실제 방송 편집처럼 자연스럽게 이어라.
- 예: [화자의 대사] + [듣는 사람들의 리액션 풀샷] + [터지는 펀치라인 클로즈업]

규칙:
- 각 조각은 최소 1.5초 이상으로, 너무 잘게 쪼개지 마라.
- 조각 사이의 지루하거나 늘어지는 부분은 과감히 빼라.
- 조각은 2~6개, 이어붙인 총 길이는 최대 {max_sec}초.
- 완성된 하이라이트는 그 자체로 맥락이 이해되고 끝까지 보게 만들어야 한다.
- 각 조각은 말/샷이 자연스럽게 시작·끝나는 지점에서 자르고, 문장·동작 중간을 끊지 마라.

반드시 아래 JSON 형식으로만 답하라 (설명 텍스트 금지):
{{
  "clips": [
    {{
      "title": "한 줄 제목 ({lang_hint})",
      "reason": "이 하이라이트가 왜 재미있는지/무엇을 노렸는지 ({lang_hint}, 한 문장)",
      "score": 0.95,
      "segments": [
        {{"start": "0:12", "end": "0:18"}},
        {{"start": "1:30", "end": "1:42"}}
      ]
    }}
  ]
}}"""

    return common + f"""

[편집 방식 = 단일 연속 구간]
각 하이라이트는 하나의 연속된 구간이다.
- 각 구간은 그 자체로 맥락이 이해되어야 한다 (말/장면 중간에서 시작·끝나지 않게).
- 길이는 최대 {max_sec}초, 너무 짧지 않게 (8초 이상 권장).
- 구간끼리 시간대가 겹치지 않게.

반드시 아래 JSON 형식으로만 답하라 (설명 텍스트 금지):
{{
  "clips": [
    {{
      "title": "한 줄 제목 ({lang_hint})",
      "reason": "이 구간을 고른 이유 ({lang_hint}, 한 문장)",
      "score": 0.95,
      "segments": [ {{"start": "0:12", "end": "0:41"}} ]
    }}
  ]
}}"""


def _parse_time(v) -> float | None:
    """Accept 12.5, "12.5", "0:12", "1:02:03" → seconds."""
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if not s:
        return None
    if ":" in s:
        try:
            parts = [float(p) for p in s.split(":")]
        except ValueError:
            return None
        sec = 0.0
        for p in parts:
            sec = sec * 60 + p
        return sec
    try:
        return float(s)
    except ValueError:
        return None


def _clean_segments(raw, max_sec: int) -> list[list[float]]:
    """Validate, sort, merge-overlap, and total-cap a clip's segment list."""
    segs = []
    for s in raw or []:
        a = _parse_time(s.get("start") if isinstance(s, dict) else None)
        b = _parse_time(s.get("end") if isinstance(s, dict) else None)
        if a is None or b is None:
            continue
        if b - a >= 0.4:
            segs.append([round(a, 2), round(b, 2)])
    if not segs:
        return []
    segs.sort(key=lambda x: x[0])
    # merge overlaps / tiny gaps
    merged = [segs[0]]
    for a, b in segs[1:]:
        if a <= merged[-1][1] + 0.1:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    # cap cumulative duration at max_sec (+small grace)
    out, acc = [], 0.0
    for a, b in merged:
        if acc >= max_sec:
            break
        dur = b - a
        if acc + dur > max_sec + 3:
            b = a + (max_sec + 3 - acc)
            dur = b - a
        out.append([a, round(b, 2)])
        acc += dur
    return out


def analyze_highlights(
    video_path: str,
    n_clips: int = 3,
    max_sec: int = 60,
    heatmap_peaks: list[dict] | None = None,
    lang_hint: str = "한국어",
    montage: bool = True,
    duration_sec: float = 0.0,
    progress=None,
) -> list[dict]:
    """Upload the video to Gemini and return highlight clips.

    Each clip: {title, reason, score, segments:[[start,end],...], start, end, duration}
    `segments` may contain multiple beats (montage) or one (single).
    """
    from google import genai
    from google.genai import types

    def say(msg: str):
        if progress:
            progress(msg)

    client = genai.Client(api_key=_get_api_key())

    say("Gemini에 영상 업로드 중…")
    uploaded = client.files.upload(file=video_path)

    say("Gemini 영상 처리 대기 중…")
    waited = 0
    while uploaded.state and uploaded.state.name == "PROCESSING":
        time.sleep(3)
        waited += 3
        uploaded = client.files.get(name=uploaded.name)
        if waited > 600:
            raise RuntimeError("Gemini 영상 처리 시간 초과(10분).")

    if uploaded.state and uploaded.state.name == "FAILED":
        raise RuntimeError("Gemini 영상 처리 실패.")

    say("Gemini가 영상을 분석하는 중…")
    prompt = _build_prompt(n_clips, max_sec, heatmap_peaks or [], lang_hint, montage, duration_sec)
    resp = client.models.generate_content(
        model=MODEL,
        contents=[uploaded, prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.4,
        ),
    )

    try:
        client.files.delete(name=uploaded.name)
    except Exception:
        pass

    data = json.loads(resp.text)
    clips = data.get("clips", []) if isinstance(data, dict) else []
    print(f"[gemini] raw clips returned: {len(clips)}")

    cleaned = []
    for c in clips:
        if not isinstance(c, dict):
            continue
        # support both {segments:[...]} and legacy {start,end}
        raw_segs = c.get("segments")
        if not raw_segs and c.get("start") is not None and c.get("end") is not None:
            raw_segs = [{"start": c["start"], "end": c["end"]}]
        segs = _clean_segments(raw_segs, max_sec)
        if not segs:
            print(f"[gemini] dropped clip (no valid segments): {c.get('segments') or c}")
            continue
        cleaned.append({
            "title":    str(c.get("title", "")).strip()[:80],
            "reason":   str(c.get("reason", "")).strip()[:200],
            "score":    float(c.get("score", 0.0) or 0.0),
            "segments": segs,
            "start":    segs[0][0],
            "end":      segs[-1][1],
            "duration": round(sum(b - a for a, b in segs), 2),
        })

    cleaned.sort(key=lambda c: c["score"], reverse=True)
    print(f"[gemini] usable clips: {len(cleaned)} "
          f"durations={[round(c['duration'],1) for c in cleaned]}")
    return cleaned[:n_clips]
