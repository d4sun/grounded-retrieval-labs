#!/usr/bin/env bash
# Install the real free stack WITHOUT the ~1-2 GB CUDA wheels.
#
# sentence-transformers depends on PyTorch, and a plain `pip install torch` on Linux
# pulls the CUDA build (nvidia-cudnn-cu13 & friends, ~519 MB each). This lab is CPU-only,
# so we install CPU PyTorch FIRST from PyTorch's CPU index; the extras then reuse it.
set -euo pipefail
cd "$(dirname "$0")/.."

PIP="${PIP:-pip}"

echo "==> 1/2  CPU-only PyTorch (no CUDA)"
$PIP install torch --index-url https://download.pytorch.org/whl/cpu

echo "==> 2/2  Free extras (reuse the CPU torch already installed)"
$PIP install -e ".[free]"

echo "==> Verify"
python -c "import torch; print('torch', torch.__version__, '| CUDA build:', torch.version.cuda)"
echo "If 'CUDA build: None' above, you're CPU-only as intended."
