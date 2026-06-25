# capcut-auto-cut 🎬✂️

영상에서 **사람 음성이 없는 구간(무음)을 밀리초(ms) 단위로 감지·자동 컷편집**하고,
싱크가 완벽한 **SRT 자막**을 함께 내보내는 Windows 11 데스크톱 앱.

- **VAD(음성 감지):** Silero-VAD (ONNX) — 단순 dB가 아닌 AI로 '사람 목소리'만 판별
- **자막:** faster-whisper(Whisper STT)로 실제 받아쓰기 → SRT 출력
- **GUI:** CustomTkinter 모던 다크 테마, 최소 무음 길이 ms 단위 조절
- **배포:** PyInstaller `--onefile` 단일 `.exe` 실행 파일 (VAD 모델 + FFmpeg 내장)

> ⚠️ **확인 필요 (중요):** 최종 단일 실행 파일(`.exe`)은 **Windows에서 빌드**해야
> Windows에서 실행됩니다. PyInstaller는 빌드한 OS 전용 실행 파일만 만듭니다.

---

## 진행 단계

- [x] **1단계** — 가상환경 구축 + 필수 라이브러리 설치  ← *현재 여기*
- [ ] 2단계 — `resource_path` 포함 CustomTkinter UI
- [ ] 3단계 — VAD + 영상 편집 + STT 백엔드 로직
- [ ] 4단계 — PyInstaller Spec 파일 & 빌드

---

## 1단계: 가상환경 구축 & 라이브러리 설치 (Windows 11)

### 0) 사전 준비 — Python 설치 확인

**PowerShell** 또는 **명령 프롬프트(cmd)**를 열고:

```powershell
py --version
```

`Python 3.11.x` 또는 `3.10.x`가 나오면 좋습니다.

> ⚠️ **확인 필요 — Python 설치:**
> 아직 없다면 **[python.org 공식 설치 프로그램](https://www.python.org/downloads/windows/)**
> 으로 Python 3.11을 설치하세요. 설치 첫 화면에서 **반드시
> `Add python.exe to PATH` 체크박스를 켜고** 진행해야 터미널에서 `py`/`python`
> 명령이 바로 동작합니다.
>
> 다행히 **Windows 공식 설치본에는 `tkinter`(Tcl/Tk)가 기본 포함**되어 있어,
> macOS와 달리 CustomTkinter 관련 추가 설치가 필요 없습니다.

### 1) 프로젝트 폴더에서 가상환경 만들기

```powershell
cd capcut-auto-cut

# .venv 라는 격리된 파이썬 환경 생성
py -m venv .venv

# 가상환경 켜기 (프롬프트 앞에 (.venv) 가 붙으면 성공)
.venv\Scripts\activate
```

> 💡 **PowerShell에서 실행 정책 오류가 나면** (`...이 시스템에서 스크립트를 실행할 수
> 없으므로...`) 다음을 한 번 실행한 뒤 다시 시도하세요:
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
> ```
> cmd(명령 프롬프트)를 쓴다면 `.venv\Scripts\activate.bat` 입니다.
>
> 끄고 싶을 땐 `deactivate` 입력. 이후 작업은 항상 가상환경을 켠 상태에서 합니다.

### 2) 라이브러리 설치

```powershell
# pip 최신화
python -m pip install --upgrade pip

# requirements.txt 의 모든 라이브러리 설치
pip install -r requirements.txt
```

설치에는 몇 분 걸릴 수 있습니다(특히 onnxruntime, ctranslate2).

### 3) VAD 모델 내려받기

```powershell
python scripts\download_models.py
```

`models\silero_vad.onnx` 파일이 생기면 성공입니다.

### 4) 설치 검증 ✅

```powershell
python scripts\verify_env.py
```

모든 줄이 `[OK]`로 나오고 마지막에 **"1단계 완료"** 가 보이면 끝입니다.

특히 다음 두 줄을 꼭 확인하세요:
- `[OK] tkinter` — Windows에서는 보통 자동으로 잡힙니다
- `[OK] ffmpeg ...\ffmpeg.exe` — 영상 처리용 FFmpeg 경로

문제가 있으면 출력된 `[FAIL]` 메시지를 그대로 알려주세요. 다음 단계로 넘어가기 전에 함께 해결합니다.
