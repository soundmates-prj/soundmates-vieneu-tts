@echo off
echo ========================================================
echo Khoi dong Server VieNeu-TTS (Audio Generator API)
echo ========================================================
echo.

echo Dang kiem tra moi truong python ao (venv)...
if not exist "venv\Scripts\activate.bat" (
    echo [!] Khong tim thay venv. Dang tao moi truong ao moi...
    python -m venv venv
    
    echo [!] Dang kich hoat venv...
    call venv\Scripts\activate.bat
    
    echo [!] Dang tai va cai dat cac thu vien can thiet...
    pip install fastapi uvicorn pydantic numpy huggingface_hub vieneu trafilatura python-multipart
) else (
    echo [OK] Da tim thay venv. Dang kich hoat...
    call venv\Scripts\activate.bat
)

echo.
echo ===============================================================
echo BAT DAU CHAY AUDIO SERVER API TAI PORT 8008 (CHO TEXT -> AUDIO)
echo ===============================================================
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
python apps\web_stream.py

echo.
echo [SERVER DA DUNG]
pause
