#!/usr/bin/env python3
"""
CLI: replay a JSON file produced by ``record_leader_poses.py`` on the SO101 **Follower**.

No manual pre-positioning: on start the arm ramps from current encoders to **home**
(default: the ``idle`` entry in the recording).

Per action:
  1) Ramp to **home** (small per-joint steps, ``--approach-max-deg``) to avoid clamp warnings.
  2) Ramp to the first recorded frame, play trajectory at fps × ``--trajectory-time-scale``.
  3) Ramp back to **home**.

Prerequisites: USB on the **follower** board; calibration matches ``--robot-id``.

  conda activate lerobot
  python arm_driver/replay_leader_poses.py --port /dev/ttyACM0 \\
    --recording recordings/leader_poses_YYYYMMDD_HHMMSS.json
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from arm_driver.replay_engine import (
    SuppressLeRobotClampWarningFilter,
    import_so101_follower,
    is_serial_permission_error,
    load_recording,
    replay_one_action,
    resolve_home_pose,
    step_toward_target,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default playback order (matches record_leader_poses.py menu order).
DEFAULT_ACTION_KEYS: list[str] = [
    "point_west",
    "point_east",
    "idle",
    "greet",
    "dance",
    "point_north",
    "point_south",
    "point_southwest",
    "point_southeast",
    "point_northeast",
    "point_northwest",
    "wave_goodbye",
]


def _print_serial_permission_help(port: str) -> None:
    sys.stderr.write(
        "\nCould not open serial port (permission denied). Try: sudo chmod 666 "
        + port
        + " or add your user to the dialout group.\n\n"
    )


def _latest_recording(recordings_dir: Path) -> Path:
    files = sorted(recordings_dir.glob("leader_poses_*.json"), key=lambda p: p.stat().st_mtime)
    if not files:
        raise SystemExit(f"No leader_poses_*.json under: {recordings_dir}")
    return files[-1]


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Replay recorded joint JSON on SO101 Follower (home round-trip per action)."
    )
    parser.add_argument("--port", default="/dev/ttyACM0", help="Follower serial device")
    parser.add_argument(
        "--robot-id",
        default="my_follower_arm",
        help="Follower calibration id (matches ~/.cache/.../so_follower/<id>.json)",
    )
    parser.add_argument(
        "--recording",
        type=Path,
        default=None,
        help="leader_poses_*.json path; default: newest under recordings/",
    )
    parser.add_argument(
        "--home-action",
        default="idle",
        help="Recording key used as fixed home pose (usually idle)",
    )
    parser.add_argument(
        "--home-avg-frames",
        type=int,
        default=20,
        help="If home is a trajectory, average first N frames for home pose",
    )
    parser.add_argument(
        "--actions",
        default=None,
        help="Comma-separated action keys; default: built-in order (skips home key unless --replay-home-source)",
    )
    parser.add_argument(
        "--replay-home-source",
        action="store_true",
        help="Also replay the --home-action entry (normally skipped)",
    )
    parser.add_argument(
        "--hold-keyframe-s",
        type=float,
        default=1.5,
        help="Hold time at keyframe target pose (seconds)",
    )
    parser.add_argument(
        "--approach-max-deg",
        type=float,
        default=7.0,
        help="Max per-joint step (deg) when ramping; smaller = slower, fewer clamp warnings",
    )
    parser.add_argument(
        "--approach-sleep",
        type=float,
        default=0.055,
        help="Sleep between ramp steps (seconds)",
    )
    parser.add_argument(
        "--trajectory-time-scale",
        type=float,
        default=1.5,
        help="Trajectory frame interval multiplier (>1 slower). 1.0 = recorded pace",
    )
    parser.add_argument(
        "--max-relative-target",
        type=float,
        default=None,
        help="LeRobot max_relative_target (deg); default max(12, approach-max-deg+4)",
    )
    parser.add_argument(
        "--tol-deg",
        type=float,
        default=3.5,
        help="Tolerance (deg) to consider home/keyframe reached",
    )
    parser.add_argument(
        "--plateau-exit-after",
        type=int,
        default=160,
        help="Exit ramp if error plateaus for this many steps; 0 disables",
    )
    parser.add_argument(
        "--no-auto-calibrate",
        action="store_true",
        help="connect(calibrate=False) when calibration already on motors",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse JSON and print play order only; no hardware",
    )
    parser.add_argument(
        "--progress-every",
        type=int,
        default=120,
        help="Log max joint error every N ramp steps; 0 disables",
    )
    parser.add_argument(
        "--quiet-clamp",
        action="store_true",
        help="Filter LeRobot 'Relative goal position magnitude had to be clamped' WARNING lines",
    )
    args = parser.parse_args()

    if args.quiet_clamp:
        logging.getLogger().addFilter(SuppressLeRobotClampWarningFilter())

    if args.max_relative_target is None:
        args.max_relative_target = max(12.0, float(args.approach_max_deg) + 4.0)

    rec_path = args.recording
    if rec_path is None:
        rec_path = _latest_recording(root / "recordings")
    rec_path = rec_path.resolve()
    if not rec_path.is_file():
        raise SystemExit(f"Recording file not found: {rec_path}")

    data = load_recording(rec_path)
    actions_data: dict[str, Any] = data.get("actions") or {}

    home = resolve_home_pose(
        data,
        home_action=args.home_action,
        avg_frames=max(1, args.home_avg_frames),
    )

    if args.actions:
        order = [x.strip() for x in args.actions.split(",") if x.strip()]
    else:
        skip_home = args.home_action if not args.replay_home_source else None
        order = [k for k in DEFAULT_ACTION_KEYS if k in actions_data and k != skip_home]
        for k in actions_data:
            if k == skip_home:
                continue
            if k not in order:
                order.append(k)

    missing = [k for k in order if k not in actions_data]
    if missing:
        raise SystemExit(f"Recording missing actions: {missing}")

    logger.info("Recording: %s", rec_path)
    logger.info("Home from action '%s' (%d joint keys)", args.home_action, len(home))
    logger.info("Playback order: %s", order)

    if args.dry_run:
        logger.info("dry-run: not connecting to hardware.")
        return

    SO101Follower, SO101FollowerConfig = import_so101_follower()
    config = SO101FollowerConfig(
        port=args.port,
        id=args.robot_id,
        use_degrees=True,
        max_relative_target=args.max_relative_target,
        cameras={},
    )
    robot = SO101Follower(config)

    try:
        robot.connect(calibrate=not args.no_auto_calibrate)
    except Exception as e:
        if is_serial_permission_error(e):
            _print_serial_permission_help(args.port)
        raise SystemExit(1) from e

    if not robot.bus.calibration:
        robot.disconnect()
        raise SystemExit(
            "Follower has no calibration; run lerobot-calibrate or omit --no-auto-calibrate."
        )

    try:
        robot.bus.enable_torque()
        logger.info("Requested enable_torque on all motors.")

        logger.info(
            "Ramping to home (max %.1f deg/step, %.3fs sleep)…",
            args.approach_max_deg,
            args.approach_sleep,
        )
        step_toward_target(
            robot,
            home,
            max_step_deg=args.approach_max_deg,
            tol_deg=args.tol_deg,
            sleep_s=args.approach_sleep,
            log_every=args.progress_every,
            plateau_exit_after=args.plateau_exit_after,
        )
        time.sleep(0.2)

        for key in order:
            zh = (actions_data[key].get("label_zh")) or key
            logger.info("Playing: %s (%s)", zh, key)
            replay_one_action(
                robot,
                home,
                actions_data[key],
                hold_keyframe_s=args.hold_keyframe_s,
                tol_deg=args.tol_deg,
                approach_max_deg=args.approach_max_deg,
                approach_sleep=args.approach_sleep,
                trajectory_time_scale=args.trajectory_time_scale,
                log_every=args.progress_every,
                plateau_exit_after=args.plateau_exit_after,
            )
            time.sleep(0.15)

        logger.info("All actions finished; arm should rest near home.")
    finally:
        robot.disconnect()


if __name__ == "__main__":
    main()
