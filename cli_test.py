"""
1단 검증용 CLI: python cli_test.py <video.mp4>
"""
import sys
from pathlib import Path
from vad import detect_speech
from draft import build_draft


def main():
    if len(sys.argv) < 2:
        print("Usage: python cli_test.py <video.mp4|mov>")
        sys.exit(1)

    video_path = sys.argv[1]
    p = Path(video_path)
    if not p.exists():
        print(f"File not found: {video_path}")
        sys.exit(1)

    print(f"[1/2] Detecting speech (WebRTC VAD) in: {p.name}")
    total, keep = detect_speech(video_path)
    print(f"      Total: {total:.1f}s  |  Keep segments: {len(keep)}")
    removed = total - sum(e - s for s, e in keep)
    print(f"      Removed: {removed:.1f}s ({removed/total*100:.0f}%)")

    print("[2/2] Building CapCut draft...")
    draft_name = f"autocut_{p.stem}"
    draft_dir = build_draft(
        video_path=str(p.resolve()),
        keep_ranges=keep,
        total_duration=total,
        draft_name=draft_name,
    )
    print(f"\n✓ Draft created: {draft_dir}")
    print("  → Open CapCut and play the draft to verify.")


if __name__ == "__main__":
    main()
