#!/usr/bin/env python3
"""
Interactive recorder for the SO101 **Leader** arm (one control board + leader hardware).

Writes a JSON file of joint keyframes / short trajectories for later playback on the **Follower**
(see ``replay_leader_poses.py`` / ``arm_daemon.py`` and ``arm_driver/README.md``).

Prerequisites:
  - USB connected to the **leader** board (not follower).
  - Valid calibration in RAM (``calibration`` non-empty), or run with default
    ``connect(calibrate=True)`` for interactive LeRobot calibration; alternatively run
    ``lerobot-calibrate --teleop.type=so101_leader --teleop.port=... --teleop.id=<leader-id>``.

Usage (``conda activate lerobot``)::

  cd /path/to/welcome
  python arm_driver/record_leader_poses.py --port /dev/ttyACM0

Import check only::

  python arm_driver/record_leader_poses.py --dry-run

Operator-facing prompts below remain in Chinese for local demos.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Menu entries: logical key, Chinese label for UI, dynamic=motion capture recommended.
ACTIONS: list[dict[str, object]] = [
    {"key": "point_west", "zh": "指西边", "dynamic": False},
    {"key": "point_east", "zh": "指东边", "dynamic": False},
    {"key": "idle", "zh": "待机动作", "dynamic": False},
    {"key": "greet", "zh": "打招呼动作", "dynamic": True},
    {"key": "dance", "zh": "跳舞动作", "dynamic": True},
    {"key": "point_north", "zh": "指北边", "dynamic": False},
    {"key": "point_south", "zh": "指南边", "dynamic": False},
    {"key": "point_southwest", "zh": "指西南", "dynamic": False},
    {"key": "point_southeast", "zh": "指东南", "dynamic": False},
    {"key": "point_northeast", "zh": "指东北", "dynamic": False},
    {"key": "point_northwest", "zh": "指西北", "dynamic": False},
    {"key": "wave_goodbye", "zh": "拜拜", "dynamic": True},
]


def _import_leader():
    """Import SO101Leader; exit with a clear message if lerobot is missing."""
    try:
        from lerobot.teleoperators.so_leader import SO101Leader, SO101LeaderConfig
    except ImportError as e:
        raise SystemExit(
            "Could not import lerobot (SO101Leader). Run inside the `lerobot` conda env.\n"
            f"Original error: {e}"
        ) from e
    return SO101Leader, SO101LeaderConfig


def _round_action(action: dict[str, float], ndigits: int = 4) -> dict[str, float]:
    return {k: round(float(v), ndigits) for k, v in sorted(action.items())}


def capture_keyframe(get_action, samples: int = 20, interval_s: float = 0.02) -> dict[str, float]:
    """Average ``samples`` readings to reduce hand jitter."""
    acc: defaultdict[str, float] = defaultdict(float)
    for _ in range(samples):
        a = get_action()
        for k, v in a.items():
            acc[k] += float(v)
    n = float(samples)
    return {k: acc[k] / n for k in sorted(acc.keys())}


def capture_trajectory(get_action, duration_s: float, fps: float) -> list[dict[str, float]]:
    """Sample ``get_action`` at ``fps`` for ``duration_s`` seconds."""
    frames: list[dict[str, float]] = []
    dt = 1.0 / fps
    t_end = time.perf_counter() + duration_s
    while time.perf_counter() < t_end:
        frames.append(_round_action(get_action()))
        time.sleep(dt)
    return frames


def _default_out_path() -> Path:
    root = Path(__file__).resolve().parents[1]
    out_dir = root / "recordings"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return out_dir / f"leader_poses_{ts}.json"


def _expected_calibration_path(leader_id: str) -> Path:
    return Path.home() / ".cache/huggingface/lerobot/calibration/teleoperators/so_leader" / f"{leader_id}.json"


def _print_actions(recorded: set[str]) -> None:
    for i, item in enumerate(ACTIONS, start=1):
        key = str(item["key"])
        zh = str(item["zh"])
        mark = "✓" if key in recorded else "·"
        hint = "（建议轨迹）" if item.get("dynamic") else ""
        print(f"  {mark} {i:2d}. {zh} [{key}]{hint}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Record SO101 Leader joint poses / trajectories to JSON (interactive)."
    )
    parser.add_argument("--port", default="/dev/ttyACM0", help="Leader board serial device")
    parser.add_argument(
        "--leader-id",
        default="my_leader_arm",
        help="Leader calibration id (matches ~/.cache/.../so_leader/<id>.json)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Output JSON path (default: welcome/recordings/leader_poses_<UTC>.json)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Verify lerobot import only; do not open hardware",
    )
    parser.add_argument(
        "--keyframe-samples",
        type=int,
        default=20,
        help="Number of samples averaged per static keyframe",
    )
    parser.add_argument("--trajectory-fps", type=float, default=30.0, help="Trajectory capture FPS")
    parser.add_argument(
        "--trajectory-seconds",
        type=float,
        default=6.0,
        help="Default trajectory duration (seconds) in interactive mode",
    )
    parser.add_argument(
        "--no-auto-calibrate",
        action="store_true",
        help=(
            "connect(calibrate=False). Use only when calibration already matches motors; "
            "otherwise you may see has no calibration registered."
        ),
    )
    args = parser.parse_args()

    SO101Leader, SO101LeaderConfig = _import_leader()
    if args.dry_run:
        logger.info("dry-run: SO101Leader 导入成功。")
        sys.exit(0)

    config = SO101LeaderConfig(port=args.port, id=args.leader_id, use_degrees=True)
    leader = SO101Leader(config)

    out_path = args.output or _default_out_path()
    payload: dict = {
        "version": 1,
        "leader_id": args.leader_id,
        "port": args.port,
        "use_degrees": True,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "actions": {},
    }

    recorded: set[str] = set()

    do_cal = not args.no_auto_calibrate
    logger.info(
        "连接 Leader（calibrate=%s）：无标定或与电机不一致时会进入 LeRobot 标定/同步流程…",
        do_cal,
    )
    try:
        leader.connect(calibrate=do_cal)
    except Exception as e:
        logger.exception("连接失败: %s", e)
        raise SystemExit(1) from e

    if not leader.bus.calibration:
        leader.disconnect()
        cp = _expected_calibration_path(args.leader_id)
        sys.stderr.write(
            "\n错误：总线上没有标定数据（calibration 为空）。\n\n"
            "请不要加 --no-auto-calibrate，直接重跑本脚本以完成标定；或先手动：\n"
            f"  lerobot-calibrate --teleop.type=so101_leader --teleop.port={args.port} "
            f"--teleop.id={args.leader_id}\n\n"
            f"期望的标定文件路径（供核对）：\n  {cp}\n\n"
        )
        raise SystemExit(1)

    print()
    print("========== Leader 动作录制 ==========")
    print(f"串口: {args.port}   标定 id: {args.leader_id}")
    print(f"输出文件: {out_path}")
    print("说明：静态动作摆稳后做快照；打招呼/跳舞/拜拜可用轨迹。")
    print()

    try:
        while True:
            _print_actions(recorded)
            print()
            raw = input("选择 1–12 录制对应动作，s=保存退出，q=不保存退出: ").strip().lower()

            if raw == "q":
                print("已放弃保存。")
                return
            if raw == "s":
                break

            try:
                idx = int(raw)
            except ValueError:
                print("请输入 1–12、s 或 q。\n")
                continue

            if idx < 1 or idx > len(ACTIONS):
                print("编号应在 1–12 之间。\n")
                continue

            spec = ACTIONS[idx - 1]
            key = str(spec["key"])
            zh = str(spec["zh"])
            is_dyn = bool(spec.get("dynamic"))

            print()
            print(f"—— 当前：{zh} ({key}) ——")
            if is_dyn:
                print("该动作建议用轨迹 [t]；也可用快照 [k] 只记一个姿势。")
            else:
                print("该动作用快照 [k] 即可。")

            sub = input("模式 [k] 快照 / [t] 轨迹 / [c] 取消: ").strip().lower() or "k"
            if sub == "c":
                print()
                continue

            if sub == "k":
                input(f"摆好「{zh}」，保持稳定，然后按 Enter 开始采集快照…")
                pose = capture_keyframe(leader.get_action, samples=args.keyframe_samples)
                payload["actions"][key] = {
                    "label_zh": zh,
                    "kind": "keyframe",
                    "action": _round_action(pose),
                }
                recorded.add(key)
                print(f"已记录快照（{args.keyframe_samples} 次平均）。")

            elif sub == "t":
                sec_s = input(
                    f"录制秒数 [{args.trajectory_seconds}]: "
                ).strip()
                sec = float(sec_s) if sec_s else args.trajectory_seconds
                print(f"开始录制 {sec:.1f} 秒 —— 现在做「{zh}」动作…")
                time.sleep(0.3)
                frames = capture_trajectory(
                    leader.get_action,
                    duration_s=sec,
                    fps=args.trajectory_fps,
                )
                payload["actions"][key] = {
                    "label_zh": zh,
                    "kind": "trajectory",
                    "fps": args.trajectory_fps,
                    "frames": frames,
                }
                recorded.add(key)
                print(f"已记录 {len(frames)} 帧。")
            else:
                print("未知模式，返回主菜单。\n")
                continue

            print()

    finally:
        leader.disconnect()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"已保存: {out_path}")
    print("下一步：把好板接到 follower 臂 → lerobot-calibrate follower → 用回放脚本发送这些关节目标。")


if __name__ == "__main__":
    main()
