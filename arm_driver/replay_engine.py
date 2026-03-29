"""
Shared replay utilities for the SO101 Follower.

Used by:
  - ``replay_leader_poses.py`` (batch CLI replay)
  - ``arm_daemon.py`` (single-action HTTP playback)

Implements ramped joint motion toward targets to stay within LeRobot safe
per-step limits, then plays recorded keyframes or trajectories.
"""

from __future__ import annotations

import json
import logging
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Substring used to identify noisy LeRobot clamp warnings in logs.
_CLAMP_WARN_NEEDLE = "Relative goal position magnitude had to be clamped"


class SuppressLeRobotClampWarningFilter(logging.Filter):
    """Drops log records whose message contains the LeRobot clamp warning needle."""

    def filter(self, record: logging.LogRecord) -> bool:
        return _CLAMP_WARN_NEEDLE not in record.getMessage()


def import_so101_follower():
    """Import SO101Follower from lerobot; exit with instructions if import fails."""
    try:
        from lerobot.robots.so_follower import SO101Follower, SO101FollowerConfig
    except ImportError as e:
        raise SystemExit(
            "Could not import lerobot (SO101Follower). Run inside the `lerobot` conda env.\n"
            f"Original error: {e}"
        ) from e
    return SO101Follower, SO101FollowerConfig


def is_serial_permission_error(exc: BaseException) -> bool:
    """True if the exception chain indicates serial permission denied."""
    cur: BaseException | None = exc
    while cur is not None:
        if isinstance(cur, PermissionError) and getattr(cur, "errno", None) == 13:
            return True
        if "permission denied" in str(cur).lower():
            return True
        cur = cur.__cause__ or cur.__context__
    return False


def load_recording(path: Path) -> dict[str, Any]:
    """Load a leader_poses JSON file."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def mean_pose(frames: list[dict[str, float]], joint_keys: list[str]) -> dict[str, float]:
    """Per-joint arithmetic mean over the given frames."""
    acc: defaultdict[str, float] = defaultdict(float)
    for fr in frames:
        for k in joint_keys:
            acc[k] += float(fr[k])
    n = len(frames)
    return {k: acc[k] / n for k in joint_keys}


def resolve_home_pose(
    data: dict[str, Any],
    *,
    home_action: str,
    avg_frames: int,
) -> dict[str, float]:
    """
    Resolve the neutral 'home' pose from a recording entry (keyframe or trajectory).

    For trajectories, averages the first ``avg_frames`` frames.
    """
    actions = data.get("actions") or {}
    if home_action not in actions:
        raise SystemExit(
            f"Recording has no action '{home_action}' for home. "
            "Use --home-action to select an existing key."
        )
    block = actions[home_action]
    kind = block.get("kind")
    if kind == "keyframe":
        return {k: float(v) for k, v in block["action"].items()}
    if kind == "trajectory":
        frames: list = block.get("frames") or []
        if not frames:
            raise SystemExit(f"Action '{home_action}' has an empty trajectory.")
        keys = sorted(frames[0].keys())
        n = min(avg_frames, len(frames))
        return mean_pose(frames[:n], keys)
    raise SystemExit(f"Unknown block kind: {kind}")


def step_toward_target(
    robot,
    target: dict[str, float],
    *,
    max_step_deg: float,
    tol_deg: float,
    sleep_s: float,
    max_steps: int = 30_000,
    log_every: int = 0,
    stall_warn_after: int = 80,
    plateau_exit_after: int = 160,
) -> None:
    """
    Move from current encoder feedback toward ``target`` in small per-joint steps
    (at most ``max_step_deg`` per step) until within ``tol_deg``.

    If joint error plateaus for ``plateau_exit_after`` iterations (stuck / limit /
    calibration mismatch), stop early to avoid an infinite loop.
    """
    keys = list(target.keys())
    cur0: dict[str, float] | None = None
    last_err: float | None = None
    plateau = 0
    for i in range(max_steps):
        obs = robot.get_observation()
        cur = {k: float(obs[k]) for k in keys}
        err = max(abs(float(target[k]) - cur[k]) for k in keys)
        if cur0 is None:
            cur0 = dict(cur)
        if i == stall_warn_after and cur0 is not None:
            moved = max(abs(cur[k] - cur0[k]) for k in keys)
            if moved < 0.25:
                logger.error(
                    "After ~%d steps joint feedback barely moved (max delta %.3f). "
                    "Check power, USB on the **follower** board, and torque enable.",
                    stall_warn_after,
                    moved,
                )
        if all(abs(float(target[k]) - cur[k]) <= tol_deg for k in keys):
            if i > 0 and log_every:
                logger.info("Reached target in %d steps", i)
            return

        if (
            plateau_exit_after > 0
            and i >= 80
            and last_err is not None
            and abs(err - last_err) < 0.06
        ):
            plateau += 1
        else:
            plateau = 0
        last_err = err
        if plateau_exit_after > 0 and plateau >= plateau_exit_after:
            logger.warning(
                "Max joint error ~%.2f deg unchanged for %d steps "
                "(limit or leader/follower calibration mismatch); stopping approach.",
                err,
                plateau_exit_after,
            )
            return

        nxt: dict[str, float] = {}
        for k in keys:
            delta = float(target[k]) - cur[k]
            # Step from current feedback to avoid one huge command still being clamped.
            step = max(-max_step_deg, min(max_step_deg, delta))
            nxt[k] = cur[k] + step
        robot.send_action(nxt)
        if log_every and i > 0 and i % log_every == 0:
            logger.info("Approaching… step=%d max_err~%.2f deg", i, err)
        time.sleep(sleep_s)
    logger.warning(
        "step_toward_target: did not converge in %d steps (tol %.2f deg)", max_steps, tol_deg
    )


def replay_trajectory_segment(
    robot,
    frames: list[dict[str, float]],
    *,
    fps: float,
    time_scale: float,
) -> None:
    """Send trajectory frames at fps * time_scale."""
    if not frames:
        return
    base_dt = 1.0 / fps if fps > 0 else 0.033
    dt = base_dt * max(0.05, time_scale)
    for fr in frames:
        robot.send_action(fr)
        time.sleep(dt)


def replay_one_action(
    robot,
    home: dict[str, float],
    block: dict[str, Any],
    *,
    hold_keyframe_s: float,
    tol_deg: float,
    approach_max_deg: float,
    approach_sleep: float,
    trajectory_time_scale: float,
    log_every: int,
    plateau_exit_after: int,
) -> None:
    """
    Play one action block: approach first pose, play body, return to ``home``.

    Supports ``kind`` ``keyframe`` (single pose + hold) and ``trajectory``.
    """
    kind = block.get("kind")
    if kind == "keyframe":
        target = {k: float(v) for k, v in block["action"].items()}
        step_toward_target(
            robot,
            target,
            max_step_deg=approach_max_deg,
            tol_deg=tol_deg,
            sleep_s=approach_sleep,
            log_every=log_every,
            plateau_exit_after=plateau_exit_after,
        )
        time.sleep(max(0.0, hold_keyframe_s))
        step_toward_target(
            robot,
            home,
            max_step_deg=approach_max_deg,
            tol_deg=tol_deg,
            sleep_s=approach_sleep,
            log_every=log_every,
            plateau_exit_after=plateau_exit_after,
        )
        return

    if kind == "trajectory":
        frames_raw = block.get("frames") or []
        fps = float(block.get("fps") or 30.0)
        if not frames_raw:
            return
        frames = [{k: float(v) for k, v in fr.items()} for fr in frames_raw]
        first = frames[0]
        step_toward_target(
            robot,
            first,
            max_step_deg=approach_max_deg,
            tol_deg=tol_deg,
            sleep_s=approach_sleep,
            log_every=log_every,
            plateau_exit_after=plateau_exit_after,
        )
        rest = frames[1:] if len(frames) > 1 else []
        replay_trajectory_segment(
            robot,
            rest,
            fps=fps,
            time_scale=trajectory_time_scale,
        )
        step_toward_target(
            robot,
            home,
            max_step_deg=approach_max_deg,
            tol_deg=tol_deg,
            sleep_s=approach_sleep,
            log_every=log_every,
            plateau_exit_after=plateau_exit_after,
        )
        return

    raise RuntimeError(f"Unknown block kind: {kind}")
