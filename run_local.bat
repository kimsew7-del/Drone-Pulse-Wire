@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist .env (
    copy .env.example .env
    echo .env 파일이 없어 기본 템플릿으로 생성했습니다.
    echo 필요한 API 키를 .env에 입력한 뒤 다시 실행하세요.
    pause
    exit /b
)

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo Python이 설치되어 있지 않습니다.
    echo https://www.python.org/downloads/ 에서 Python 3.10 이상을 설치하세요.
    echo 설치 시 "Add python.exe to PATH" 체크를 반드시 해주세요.
    pause
    exit /b
)

echo.
echo  ===================================
echo   Briefwave 서버 시작
echo   http://localhost:8080
echo  ===================================
echo.

python server.py
pause
