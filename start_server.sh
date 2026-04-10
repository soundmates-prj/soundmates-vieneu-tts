#!/usr/bin/env bash
set -euo pipefail

echo "========================================================"
echo "Khoi dong Server VieNeu-TTS (Audio Generator API)"
echo "========================================================"
echo

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

# Prefer existing venv. Create venv if neither venv nor .venv exists.
if [[ -d "venv" ]]; then
  VENV_DIR="venv"
elif [[ -d ".venv" ]]; then
  VENV_DIR=".venv"
else
  VENV_DIR="venv"
  echo "[!] Khong tim thay venv/.venv. Dang tao moi truong ao: ${VENV_DIR}"
  python3 -m venv "$VENV_DIR"
fi

echo "[!] Dang kich hoat ${VENV_DIR}..."
# shellcheck source=/dev/null
source "${VENV_DIR}/bin/activate"

echo "[!] Dang kiem tra va cai thu vien con thieu..."
if ! python -c "import fastapi,uvicorn,pydantic,numpy,huggingface_hub,vieneu,trafilatura,multipart" >/dev/null 2>&1; then
  echo "[!] Phat hien thieu thu vien. Dang cai dat..."
  python -m pip install --upgrade pip
  python -m pip install --prefer-binary \
    --extra-index-url https://pnnbao97.github.io/llama-cpp-python-v0.3.16/cpu/ \
    fastapi uvicorn pydantic numpy huggingface_hub vieneu trafilatura python-multipart
fi

echo
echo "==============================================================="
echo "BAT DAU CHAY AUDIO SERVER API TAI PORT 8008 (CHO TEXT -> AUDIO)"
echo "==============================================================="
export PYTHONIOENCODING=utf-8
python apps/web_stream.py
