#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TP="$ROOT/third_party"
mkdir -p "$TP"
cd "$TP"

if [[ ! -d ultralytics ]]; then
  echo "Cloning ultralytics (depth 1)..."
  git clone --depth 1 https://github.com/ultralytics/ultralytics.git
else
  echo "Exists: $TP/ultralytics"
fi

echo "Done. API 使用仍以 pip 包为准: pip install ultralytics"
echo "LeRobot/SO101 请使用本机 ~/lerobot 或官方文档，勿在此重复克隆完整仓库。"
