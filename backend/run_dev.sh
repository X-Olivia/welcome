#!/usr/bin/env bash
set -euo pipefail
# 在 conda 环境 lerobot 中启动 API（与 LeRobot / SO-ARM101 一致）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if command -v conda >/dev/null 2>&1; then
  eval "$(conda shell.bash hook)"
else
  echo "未找到 conda，请先安装 Miniconda/Anaconda 或手动: conda activate lerobot" >&2
  exit 1
fi
conda activate lerobot
cd "$SCRIPT_DIR"
exec uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
