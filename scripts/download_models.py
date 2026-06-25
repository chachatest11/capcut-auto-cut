"""
Silero-VAD ONNX 모델 다운로드 스크립트
------------------------------------------------------------
'사람 목소리 감지' AI 모델 파일(silero_vad.onnx)을 models/ 폴더에
내려받습니다. 이 파일은 나중에 --onefile 실행파일 안에 통째로 내장됩니다.

사용법 (가상환경을 켠 상태에서):
    python scripts/download_models.py

⚠️ 확인 필요: 아래 다운로드 URL은 silero-vad 공식 깃허브 저장소를
가리킵니다. 저장소 구조가 바뀌면 URL 수정이 필요할 수 있습니다.
(인터넷 연결이 필요합니다.)
"""

import os
import sys
import urllib.request

# 모델을 저장할 위치: 프로젝트루트/models/silero_vad.onnx
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(PROJECT_ROOT, "models")
TARGET = os.path.join(MODELS_DIR, "silero_vad.onnx")

# Silero-VAD 공식 저장소의 onnx 모델 직접 링크
URL = "https://github.com/snakers4/silero-vad/raw/master/src/silero_vad/data/silero_vad.onnx"


def main():
    os.makedirs(MODELS_DIR, exist_ok=True)

    if os.path.exists(TARGET) and os.path.getsize(TARGET) > 0:
        size_kb = os.path.getsize(TARGET) / 1024
        print(f"[SKIP] 이미 존재합니다: {TARGET} ({size_kb:.0f} KB)")
        return

    print(f"[..] 다운로드 중: {URL}")
    try:
        urllib.request.urlretrieve(URL, TARGET)
    except Exception as e:  # noqa: BLE001
        print(f"[FAIL] 다운로드 실패: {e}")
        print("       인터넷 연결 또는 위 URL을 확인하세요.")
        sys.exit(1)

    size_kb = os.path.getsize(TARGET) / 1024
    print(f"[OK] 저장 완료: {TARGET} ({size_kb:.0f} KB)")
    print("     이제 'python scripts/verify_env.py' 로 환경을 검증하세요.")


if __name__ == "__main__":
    main()
