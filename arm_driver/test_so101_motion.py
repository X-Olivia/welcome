#!/usr/bin/env python3
"""
SO-ARM101 (LeRobot ``so101_follower``) connectivity and small-motion smoke test.

Prerequisites (official docs):
  - ``lerobot-setup-motors`` for motor IDs and baud rate
  - ``lerobot-calibrate`` with the same ``--robot-id`` as this script
  - Linux serial permissions: ``dialout`` group or ``chmod`` on ``/dev/ttyACM*``

Usage::

  conda activate lerobot
  cd /path/to/welcome
  python arm_driver/test_so101_motion.py --port /dev/ttyACM0

Import check only::

  python arm_driver/test_so101_motion.py --dry-run
"""

from __future__ import annotations

import argparse
import logging
import sys
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _import_robot():
    try:
        from lerobot.robots.so_follower import SO101Follower, SO101FollowerConfig
    except ImportError as e:
        raise SystemExit(
            "Could not import lerobot (SO101Follower). In the `lerobot` conda env run:\n"
            "  pip install 'lerobot[feetech]'\n"
            "or install from source per official docs.\n"
            f"Original error: {e}"
        ) from e
    return SO101Follower, SO101FollowerConfig


def _joint_keys() -> list[str]:
    return [
        "shoulder_pan",
        "shoulder_lift",
        "elbow_flex",
        "wrist_flex",
        "wrist_roll",
        "gripper",
    ]


def _obs_to_action(obs: dict) -> dict:
    """Map observation ``*.pos`` keys to the dict format expected by ``send_action``."""
    keys = _joint_keys()
    return {f"{k}.pos": float(obs[f"{k}.pos"]) for k in keys if f"{k}.pos" in obs}


def _is_serial_permission_error(exc: BaseException) -> bool:
    cur: BaseException | None = exc
    while cur is not None:
        if isinstance(cur, PermissionError) and getattr(cur, "errno", None) == 13:
            return True
        if "permission denied" in str(cur).lower():
            return True
        cur = cur.__cause__ or cur.__context__
    return False


def _print_serial_permission_help(port: str) -> None:
    sys.stderr.write(
        "\nSerial port permission denied. On Ubuntu/Debian try:\n\n"
        "  1) Temporary: sudo chmod 666 " + port + "\n"
        "  2) Permanent: add user to dialout, then re-login\n"
        "       sudo usermod -aG dialout \"$USER\"\n"
        "       groups   # should list dialout\n\n"
        "Then re-run this script.\n"
    )


def _is_no_motors_on_bus_error(exc: BaseException) -> bool:
    s = str(exc)
    return "FeetechMotorsBus motor check failed" in s or "Missing motor IDs" in s


def _print_motor_bus_help(port: str) -> None:
    sys.stderr.write(
        "\nSerial opened but no motors on the bus (empty motor list). "
        "This is wiring/power/port selection, not a Python bug.\n\n"
        "Checklist:\n"
        "  • Board USB to PC and arm power on.\n"
        "  • USB is on the **follower** board; with two ttyACM devices try:\n"
        "      lerobot-find-port\n"
        "    and pass the other device to --port.\n"
        "  • Servo bus daisy-chain from the board to the first joint.\n"
        "  • New hardware: configure IDs (official docs):\n"
        "      lerobot-setup-motors --robot.type=so101_follower --robot.port=" + port + "\n"
        "  • Some Waveshare boards need USB jumper on **B** (see LeRobot SO-101 docs).\n\n"
        "Fix hardware and re-run.\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="SO-ARM101 serial motion smoke test (LeRobot)")
    parser.add_argument("--port", default="/dev/ttyACM0", help="Motor bus serial device")
    parser.add_argument(
        "--robot-id",
        default="my_awesome_follower_arm",
        help=(
            "Calibration JSON basename (no .json), usually under "
            "~/.cache/huggingface/lerobot/calibration/robots/so_follower/"
        ),
    )
    parser.add_argument(
        "--shoulder-delta-deg",
        type=float,
        default=12.0,
        help="Delta (deg) added to current shoulder_pan; negative reverses direction",
    )
    parser.add_argument(
        "--hold-seconds",
        type=float,
        default=2.0,
        help="Hold at target pose before returning to baseline",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Import check only; do not open serial",
    )
    args = parser.parse_args()

    SO101Follower, SO101FollowerConfig = _import_robot()

    if args.dry_run:
        logger.info("dry-run: lerobot SO101Follower import OK.")
        sys.exit(0)

    # Cap per-step relative motion (deg); aligns with typical SOFollower safe defaults.
    config = SO101FollowerConfig(
        port=args.port,
        id=args.robot_id,
        use_degrees=True,
        max_relative_target=30.0,
    )
    robot = SO101Follower(config)

    logger.info("Connecting (calibrate=False; run lerobot-calibrate first if never calibrated)…")
    try:
        robot.connect(calibrate=False)
    except (ConnectionError, PermissionError, OSError) as e:
        if _is_serial_permission_error(e):
            _print_serial_permission_help(args.port)
            raise SystemExit(1) from e
        raise
    except RuntimeError as e:
        if _is_no_motors_on_bus_error(e):
            _print_motor_bus_help(args.port)
            raise SystemExit(1) from e
        raise

    try:
        obs = robot.get_observation()
        base = _obs_to_action(obs)
        logger.info("Baseline joint targets (deg): %s", {k: round(v, 2) for k, v in base.items()})

        moved = dict(base)
        sp = "shoulder_pan.pos"
        moved[sp] = float(moved[sp]) + args.shoulder_delta_deg

        logger.info("send_action: shoulder_pan %+.1f deg", args.shoulder_delta_deg)
        sent = robot.send_action(moved)
        logger.info("Sent (may be safety-clamped): shoulder_pan=%s", sent.get(sp))
        time.sleep(args.hold_seconds)

        logger.info("Returning to baseline pose…")
        robot.send_action(base)
        time.sleep(1.0)
        logger.info("Test finished.")
    finally:
        robot.disconnect()


if __name__ == "__main__":
    main()
