"""
1단계 설치 검증 스크립트
------------------------------------------------------------
가상환경에 라이브러리가 제대로 깔렸는지 한 방에 확인합니다.

사용법 (가상환경을 켠 상태에서):
    python scripts/verify_env.py

모든 줄이 [OK] 로 나오면 1단계 성공입니다.
"""

import sys


def check(name, fn):
    """라이브러리 하나를 import 해보고 결과를 예쁘게 출력하는 헬퍼."""
    try:
        result = fn()
        print(f"[OK]   {name:<16} {result}")
        return True
    except Exception as e:  # noqa: BLE001  (검증용이라 모든 예외를 잡습니다)
        print(f"[FAIL] {name:<16} -> {e}")
        return False


def main():
    print("=" * 55)
    print(" capcut-auto-cut  환경 검증")
    print("=" * 55)
    print(f"[INFO] Python      {sys.version.split()[0]}  ({sys.executable})")

    ok = True

    # GUI
    def _ctk():
        import customtkinter
        return f"v{customtkinter.__version__}"
    ok &= check("customtkinter", _ctk)

    # tkinter 자체(맥에서 자주 빠지는 부분 - CustomTkinter의 기반)
    def _tk():
        import tkinter
        return f"Tcl/Tk {tkinter.TkVersion}"
    ok &= check("tkinter", _tk)

    # VAD 추론 엔진
    def _ort():
        import onnxruntime
        return f"v{onnxruntime.__version__}"
    ok &= check("onnxruntime", _ort)

    # STT
    def _fw():
        import faster_whisper
        return f"v{faster_whisper.__version__}"
    ok &= check("faster_whisper", _fw)

    # FFmpeg 바이너리 경로
    def _ff():
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    ok &= check("ffmpeg", _ff)

    # numpy
    def _np():
        import numpy
        return f"v{numpy.__version__}"
    ok &= check("numpy", _np)

    print("=" * 55)
    if ok:
        print(" 결과: 모든 라이브러리 정상! 1단계 완료입니다. 🎉")
    else:
        print(" 결과: 위에 [FAIL] 이 있습니다. 해당 항목을 다시 설치하세요.")
    print("=" * 55)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
