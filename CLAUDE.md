# AutoCut (캡컷 에이전트)

한국어 말하기 영상 자동 편집기. 입력(mp4/mov 또는 유튜브 링크) → 출력: **CapCut 드래프트**(점프컷/하이라이트 + 자막).
로컬 웹앱 (FastAPI + 정적 HTML). 개인용. **크로스플랫폼(Windows + macOS)**.

## 실행
- **Windows**: `run.bat` 더블클릭 (또는 `py -m uvicorn app:app --port 8000 --reload`)
- **macOS**: `chmod +x run.command` 후 `./run.command` (또는 `python3 -m uvicorn app:app --port 8000 --reload`)
- 브라우저에서 `http://localhost:8000` 접속. HTML을 파일로 직접 열면 fetch가 깨지므로 반드시 서버 통해 접속.
- 미리보기 서버(.claude/launch.json)는 포트 **8001** (메인 8000과 충돌 방지).
- 첫 실행 시 faster-whisper medium(~1.5GB) + Silero 모델 다운로드(인터넷 필요).

## 두 가지 모드
1. **무음 컷 (silence)**: Silero VAD로 비음성 구간 제거 → 점프컷 + SRT + CapCut 드래프트. 전체 영상 ASR(medium). 실용 길이 ≤ ~15분.
2. **하이라이트 추출 (highlight)**: Gemini가 영상을 통째로 분석 → 재밌는 구간 N개(1~5) 선택 → **세로 9:16** 드래프트 N개 + 클립별 SRT. 유튜브면 '가장 많이 본 부분'(heatmap) 반영. 실용 길이 ≤ ~15분(안정), ~30분+는 분할 필요.

## 파일 구조
- `app.py` — FastAPI 서버. 엔드포인트: `/`, `/analyze`, `/process`, `/process-highlight`, `/open-capcut`, `/gemini-key`(GET/POST/DELETE), `/download/srt/{id}`. 인메모리 `JOBS` 레지스트리로 파일 경로 관리(유튜브 확장자 불일치 방지).
- `vad.py` — Silero VAD(음성만 감지, 음악 무시). `_decode_audio_16k`(오디오→16k mono float32, 정규화).
- `highlight.py` — Gemini(`gemini-2.5-flash`) 하이라이트 분석 + Gemini 키 관리(save/load/clear/status). **타임코드는 MM:SS 형식으로 요청**.
- `youtube.py` — yt-dlp 다운로드(ffmpeg 불필요, progressive) + heatmap 추출.
- `draft.py` — CapCut 드래프트 생성. **OS별 경로 자동 탐색**(`_find_draft_root`, `_find_font`), PLATFORM 딕트 OS 분기. 세로=원본비율 유지(contain-fit).
- `static/index.html` — 전체 UI(모드 토글, 유튜브 입력, 슬라이더, 진행률/경과/남은시간, 클립 카드, Gemini 키 입력).
- `crop.py` — 얼굴 추적 크롭. **현재 미사용**(원본비율 유지로 방향 전환하며 되돌림). 참고용 보존.
- `silence.py` — 구버전 에너지 기반 무음감지. **미사용**(vad.py로 대체).
- `cli_test.py` — CLI 검증용.
- `requirements.txt`, `run.bat`(Win), `run.command`(Mac), `.gitignore`, `.claude/launch.json`.

## 핵심 설계 결정
- **ASR**: faster-whisper `medium`, 한국어, int8 CPU. 하이라이트에선 선택된 클립 구간 오디오만 ASR(빠름).
- **무음 감지**: Silero VAD (WebRTC 아님 — 음악/효과음을 음성으로 오판하지 않도록).
- **하이라이트 AI**: Gemini 네이티브 영상 분석. 무엇이 하이라이트인지 AI 자동 판단. 화자/풀샷 인지 멀티샷 편집 프롬프트.
- **타임코드**: `분:초`(MM:SS) 문자열 강제. 이유: gemini-2.5-flash가 긴 영상에서 소수 초 타임코드를 신뢰성 있게 못 냄(0.01초 단위 이상값 반환 버그). `_parse_time`이 float/"MM:SS"/"HH:MM:SS" 모두 처리.
- **세로 9:16**: 캔버스만 9:16, **영상은 원본 비율 유지**(contain-fit, 크롭 안 함). 위아래 여백은 사용자가 CapCut 세로 템플릿(고정 자막)으로 채움.
- **편집 방식**: 몽타주(여러 조각 이어붙이기, 기본) / 단일 구간 — 실행 시 토글.
- **컷 정밀화**: 무음 컷은 ASR 단어 경계 스냅. 하이라이트는 조용한 지점 스냅(`_snap_quiet`, 비파괴).
- **SRT**: 편집(컷)된 타임라인 기준으로 생성 → CapCut 자막과 일치.
- **Gemini 키**: `~/.autocut/gemini_key`(프로젝트 밖). 우선순위: 환경변수 `GEMINI_API_KEY`/`GOOGLE_API_KEY` > 저장 파일. UI에서 입력.

## 처리 시간/길이 한계
- 하이라이트 모드가 긴 영상에 유리(ASR을 선택 구간만). 안정 상한 **~15분**(마진 포함). ~30분+는 overlap 분할 필요.
- 무음 컷은 전체 ASR(medium CPU ~3.5x 실시간) 때문에 더 짧음(~10~15분).
- 오디오를 통째 메모리에 로드(분당 ~3.7MB).

## 진행 상황 / 다음 할 일
- **[검증 대기]** MM:SS 타임코드 수정이 실제로 올바른 클립을 내는지 확인 (직전 세션에서 검증 도중 중단됨). 서버 콘솔에 `[gemini]`, `[highlight]` 진단 로그 출력됨 — 문제 시 이 로그로 원인 파악.
- (선택) 긴 영상 overlap 분할(2분 겹침) + 전역 dedup/랭킹 — 30분+ 대응. 몽타주는 청크 내로 제한되는 한계 있음.
- (선택) Gemini `response_schema`로 구조 강제, 결과가 너무 짧으면 자동 1회 재시도, 브라우저 내 클립 미리보기, 자막 번인.
- (선택) 업로드 시 15분 초과 경고.
- crop.py는 dead code(향후 부활 가능성 위해 보존).

## macOS 이관 시 확인
- CapCut 드래프트 경로는 `_find_draft_root`가 자동 탐색하나, 실제 존재 확인 필요:
  `~/Movies/CapCut/User Data/Projects/com.lveditor.draft` (직접 다운로드판) 또는 Mac App Store 샌드박스 컨테이너.
  실제 경로가 다르면 `draft.py`의 후보 목록에 추가.
- Windows 동작은 크로스플랫폼 전환 후에도 그대로 유지됨(검증 완료).

## 개발/배포
- 컴파일 불필요한 Python 프로젝트. 한 코드베이스가 Windows/macOS 모두 실행.
- Git 저장소: `https://github.com/chachatest11/capcut-auto-cut.git`
- 다른 PC에서 이어가기: clone → `pip install -r requirements.txt` → 실행. 이 CLAUDE.md가 맥락을 전달함.
