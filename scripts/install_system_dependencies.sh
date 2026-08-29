#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${GSPLAT_PYTHON_BIN:-python3.12}"
VENV_DIR="${ROOT_DIR}/backend/.venv"
INSTALL_NERFSTUDIO="${GSPLAT_INSTALL_NERFSTUDIO:-1}"
TORCH_INDEX_URL="${GSPLAT_TORCH_INDEX_URL:-https://download.pytorch.org/whl/cu128}"

sudo apt-get update
sudo apt-get install -y \
  build-essential \
  cmake \
  colmap \
  cuda-nvcc-12-8 \
  ffmpeg \
  git \
  libgl1 \
  libglib2.0-0 \
  python3.12 \
  python3.12-dev \
  python3.12-venv

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "Python executable not found: ${PYTHON_BIN}" >&2
  echo "Set GSPLAT_PYTHON_BIN to an installed Python with venv support." >&2
  exit 1
fi

"${PYTHON_BIN}" -m venv "${VENV_DIR}"
"${VENV_DIR}/bin/python" -m pip install --upgrade pip setuptools wheel
"${VENV_DIR}/bin/python" -m pip install -r "${ROOT_DIR}/backend/requirements.txt"

if [[ "${INSTALL_NERFSTUDIO}" == "1" ]]; then
  "${VENV_DIR}/bin/python" -m pip install torch torchvision torchaudio --index-url "${TORCH_INDEX_URL}"
  "${VENV_DIR}/bin/python" -m pip install nvidia-cuda-nvcc-cu12==12.8.93
  "${VENV_DIR}/bin/python" -m pip install ninja nerfstudio
fi

echo "System packages installed with apt."
echo "Python dependencies installed in: ${VENV_DIR}"
echo "Backend startup will use this venv automatically via scripts/start_backend.sh."
echo "CUDA nvcc expected at: /usr/local/cuda-12.8/bin/nvcc"
if [[ "${INSTALL_NERFSTUDIO}" != "1" ]]; then
  echo "Nerfstudio install was skipped. Run again with GSPLAT_INSTALL_NERFSTUDIO=1 when ready."
fi
