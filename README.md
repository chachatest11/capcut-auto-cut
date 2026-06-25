# capcut-auto-cut 🎬✂️

영상에서 **사람 음성이 없는 구간(무음)을 밀리초(ms) 단위로 감지·자동 컷편집**하고,
싱크가 완벽한 **SRT 자막**을 함께 내보내는 macOS 데스크톱 앱.

- **VAD(음성 감지):** Silero-VAD (ONNX) — 단순 dB가 아닌 AI로 '사람 목소리'만 판별
- **자막:** faster-whisper(Whisper STT)로 실제 받아쓰기 → SRT 출력
- **GUI:** CustomTkinter 모던 다크 테마, 최소 무음 길이 ms 단위 조절
- **배포:** PyInstaller `--onefile` 단일 실행 파일 (VAD 모델 + FFmpeg 내장)

> ⚠️ **확인 필요 (중요):** 최종 단일 실행 파일은 **macOS에서 빌드**해야 macOS에서
> 실행됩니다. PyInstaller는 빌드한 OS 전용 실행 파일만 만듭니다.

---

## 진행 단계

- [x] **1단계** — 가상환경 구축 + 필수 라이브러리 설치  ← *현재 여기*
- [ ] 2단계 — `resource_path` 포함 CustomTkinter UI
- [ ] 3단계 — VAD + 영상 편집 + STT 백엔드 로직
- [ ] 4단계 — PyInstaller Spec 파일 & 빌드

---

## 1단계: 가상환경 구축 & 라이브러리 설치 (macOS)

### 0) 사전 준비 — Python 설치 확인

터미널(Terminal.app)을 열고:

```bash
python3 --version
```

`Python 3.11.x` 또는 `3.10.x`가 나오면 좋습니다.

> ⚠️ **확인 필요 — macOS의 tkinter 문제:**
> CustomTkinter는 파이썬의 `tkinter`에 의존합니다. 그런데 macOS에서
> **Homebrew로 깐 파이썬에는 tkinter(Tcl/Tk)가 빠져 있는 경우**가 많습니다.
> 가장 확실한 방법은 **[python.org 공식 설치 프로그램](https://www.python.org/downloads/macos/)** 으로
> Python 3.11을 설치하는 것입니다(Tcl/Tk가 함께 들어 있고, PyInstaller 빌드도 가장 안정적입니다).
> Homebrew 파이썬을 쓴다면 `brew install python-tk@3.11` 도 함께 설치하세요.

### 1) 프로젝트 폴더에서 가상환경 만들기

```bash
cd capcut-auto-cut

# .venv 라는 격리된 파이썬 환경 생성
python3 -m venv .venv

# 가상환경 켜기 (프롬프트 앞에 (.venv) 가 붙으면 성공)
source .venv/bin/activate
```

> 끄고 싶을 땐 `deactivate` 입력. 이후 작업은 항상 가상환경을 켠 상태에서 합니다.

### 2) 라이브러리 설치

```bash
# pip 최신화
python -m pip install --upgrade pip

# requirements.txt 의 모든 라이브러리 설치
pip install -r requirements.txt
```

설치에는 몇 분 걸릴 수 있습니다(특히 onnxruntime, ctranslate2).

### 3) VAD 모델 내려받기

```bash
python scripts/download_models.py
```

`models/silero_vad.onnx` 파일이 생기면 성공입니다.

### 4) 설치 검증 ✅

```bash
python scripts/verify_env.py
```

모든 줄이 `[OK]`로 나오고 마지막에 **"1단계 완료"** 가 보이면 끝입니다.

특히 다음 두 줄을 꼭 확인하세요:
- `[OK] tkinter` — 안 보이면 위 "tkinter 문제" 안내대로 해결
- `[OK] ffmpeg /…/ffmpeg` — 영상 처리용 FFmpeg 경로

문제가 있으면 출력된 `[FAIL]` 메시지를 그대로 알려주세요. 다음 단계로 넘어가기 전에 함께 해결합니다.
