@echo off
cd /d "%~dp0"
echo AutoCut 서버 시작 중...
echo http://localhost:8000 에서 열립니다.
py -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
pause
