@echo off
echo ========================================
echo URL Collector - Windows EXE 빌드
echo ========================================

REM Python 확인
python --version >nul 2>&1
if errorlevel 1 (
    echo [오류] Python이 설치되어 있지 않습니다.
    echo https://www.python.org/downloads/ 에서 설치해주세요.
    pause
    exit /b 1
)

echo [1/4] 가상환경 생성...
python -m venv .venv
call .venv\Scripts\activate.bat

echo [2/4] 의존성 설치...
pip install --upgrade pip
pip install requests customtkinter pyinstaller

echo [3/4] EXE 빌드 중...
pyinstaller url_collector.spec --clean

echo [4/4] 완료!
echo.
echo EXE 파일 위치: dist\URLCollector.exe
echo.

pause
