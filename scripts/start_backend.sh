#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}/backend"

VENV_DIR="${ROOT_DIR}/backend/.venv"

if [[ -x "${VENV_DIR}/bin/python" ]]; then
  export VIRTUAL_ENV="${VENV_DIR}"
  export PATH="${VENV_DIR}/bin:${PATH}"
fi

if [[ -x "/usr/local/cuda-12.8/bin/nvcc" ]]; then
  export CUDA_HOME="${CUDA_HOME:-/usr/local/cuda-12.8}"
  export CUDA_PATH="${CUDA_PATH:-${CUDA_HOME}}"
  export PATH="${CUDA_HOME}/bin:${PATH}"
  export LD_LIBRARY_PATH="${CUDA_HOME}/lib64:${LD_LIBRARY_PATH:-}"
fi

if [[ -x "${VENV_DIR}/bin/uvicorn" ]]; then
  if [[ "${GSPLAT_RELOAD:-0}" == "1" ]]; then
    exec "${VENV_DIR}/bin/uvicorn" app.main:app --host 0.0.0.0 --port 8000 --reload
  fi
  exec "${VENV_DIR}/bin/uvicorn" app.main:app --host 0.0.0.0 --port 8000
fi

if [[ "${GSPLAT_RELOAD:-0}" == "1" ]]; then
  exec python3.12 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
fi
exec python3.12 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
