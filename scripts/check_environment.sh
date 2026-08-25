#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${ROOT_DIR}/backend/.venv"

if [[ -x "${VENV_DIR}/bin/python" ]]; then
  export VIRTUAL_ENV="${VENV_DIR}"
  export PATH="${VENV_DIR}/bin:${PATH}"
  PYTHON_BIN="${VENV_DIR}/bin/python"
else
  PYTHON_BIN="${GSPLAT_PYTHON_BIN:-python3.12}"
fi

if [[ -x "/usr/local/cuda-12.8/bin/nvcc" ]]; then
  export CUDA_HOME="${CUDA_HOME:-/usr/local/cuda-12.8}"
  export CUDA_PATH="${CUDA_PATH:-${CUDA_HOME}}"
  export PATH="${CUDA_HOME}/bin:${PATH}"
  export LD_LIBRARY_PATH="${CUDA_HOME}/lib64:${LD_LIBRARY_PATH:-}"
fi

check_command() {
  local name="$1"
  if command -v "$name" >/dev/null 2>&1; then
    local version
    version="$("$name" -version 2>/dev/null | head -n 1 || true)"
    if [[ -z "$version" ]]; then
      version="$("$name" --version 2>/dev/null | head -n 1 || true)"
    fi
    echo "[ok] $name: ${version:-installed}"
  else
    echo "[missing] $name"
  fi
}

check_command ffmpeg
check_command ffprobe
check_command colmap
check_command ns-train
check_command ns-export
check_command ns-process-data
check_command nvcc

if command -v nvidia-smi >/dev/null 2>&1; then
  echo "[ok] nvidia-smi"
  if ! nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader; then
    echo "[warn] nvidia-smi is installed but cannot communicate with the NVIDIA driver"
  fi
else
  echo "[missing] nvidia-smi"
fi

"${PYTHON_BIN}" - <<'PY' || true
try:
    import torch
    print(f"[ok] torch: {torch.__version__}")
    print(f"[ok] cuda available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"[ok] cuda device: {torch.cuda.get_device_name(0)}")
except Exception as exc:
    print(f"[missing] torch/cuda check failed: {exc}")
PY

"${PYTHON_BIN}" - <<'PY' || true
try:
    import gsplat.cuda._wrapper as wrapper
    has_backend = hasattr(wrapper, "_C") and wrapper._C is not None
    if has_backend:
        print("[ok] gsplat CUDA backend: available")
    else:
        print("[missing] gsplat CUDA backend: unavailable")
except Exception as exc:
    print(f"[missing] gsplat CUDA backend check failed: {exc}")
PY
