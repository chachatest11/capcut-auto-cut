#!/bin/bash
# AutoCut launcher for macOS — double-click to run.
cd "$(dirname "$0")"
echo "AutoCut 서버 시작 중..."
echo "http://localhost:8000 에서 열립니다."
python3 -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
