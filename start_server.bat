@echo off
echo ========================================================
echo Khoi dong Server VieNeu-TTS (Audio Generator API)
echo ========================================================
echo.

set VENV_PYTHON=%~dp0venv\Scripts\python.exe

if not exist "%VENV_PYTHON%" (
    echo [!] Khong tim thay venv. Dang tao moi truong ao moi...
    python -m venv venv
) else (
    echo [OK] Da tim thay venv. Dang kich hoat...
)

echo [!] Dang kich hoat venv...
call venv\Scripts\activate.bat

echo [!] Dang kiem tra va cai thu vien con thieu...
python -c "import fastapi,uvicorn,pydantic,numpy,huggingface_hub,vieneu,trafilatura,multipart" > nul 2>&1
if errorlevel 1 (
    echo [!] Phat hien thieu thu vien. Dang cai dat bo thu vien can thiet...
    python -m pip install --upgrade pip
    python -m pip install --prefer-binary --extra-index-url https://pnnbao97.github.io/llama-cpp-python-v0.3.16/cpu/ fastapi uvicorn pydantic numpy huggingface_hub vieneu trafilatura python-multipart
    if errorlevel 1 (
        echo.
        echo [X] Cai dat thu vien that bai. Thuong gap do thieu wheel prebuilt hoac mang loi.
        echo [X] Da dung de tranh chay server trong trang thai loi.
        goto :END
    )
) else (
    echo [OK] Thu vien day du.
)

echo [!] Dam bao su dung local source (go PyPI version neu co)...
"%VENV_PYTHON%" -m pip uninstall -y vieneu 2>nul
"%VENV_PYTHON%" -m pip install -e . --force-reinstall --no-deps
"%VENV_PYTHON%" -m pip install fastapi uvicorn python-multipart trafilatura 2>nul

echo.
echo ===============================================================
echo BAT DAU CHAY AUDIO SERVER API TAI PORT 8008 (CHO TEXT -> AUDIO)
echo ===============================================================
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
"%VENV_PYTHON%" apps\web_stream.py

echo.
echo [SERVER DA DUNG]
:END
pause
