#!/usr/bin/env python3
"""
Face-centered tracking for SO101 **Follower**: OpenCV camera + Haar face detection,
visual servoing using **all arm joints** (pan, lift, elbow, wrist flex/roll).

Design goals vs. a simple pan/lift P-controller:
  - **EMA** on face pixel position to cut Haar jitter (reduces vertical twitch).
  - **PD** on horizontal and vertical error (derivative damps oscillation on lift).
  - **Coupled vertical chain**: one vertical command is split across ``shoulder_lift``,
    ``elbow_flex``, and ``wrist_flex`` with per-joint step caps so joints work together
    instead of fighting.
  - **Wrist roll** adds a small horizontal trim from the same smoothed x error.
  - **Gripper** is held at the startup baseline (not used for tracking).

Prerequisites:
  - Same as ``test_so101_motion.py`` (lerobot env, calibrated follower).
  - ``pip install -r arm_driver/requirements-opencv.txt`` (or ``opencv-python``).

Typical camera (V4L2)::

  lerobot-find-cameras opencv
  python arm_driver/face_track_follower.py --camera /dev/video0 --port /dev/ttyACM0

Direction: ``--invert-pan``; for the whole vertical chain use ``--invert-vertical``.
On first valid face lock, the script can optionally run one greeting gesture from a
recording JSON, then return to tracking.
Press **q** in the preview window to quit (or Ctrl+C if ``--no-preview``).
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from arm_driver.replay_engine import load_recording, replay_one_action, resolve_home_pose

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def _import_robot():
    try:
        from lerobot.robots.so_follower import SO101Follower, SO101FollowerConfig
    except ImportError as e:
        raise SystemExit(
            "Could not import lerobot (SO101Follower). Use the `lerobot` conda env.\n"
            f"Original error: {e}"
        ) from e
    return SO101Follower, SO101FollowerConfig


def _import_cv2():
    try:
        import cv2  # noqa: PLC0415
    except ImportError as e:
        raise SystemExit(
            "OpenCV is required. Install with:\n"
            "  pip install -r arm_driver/requirements-opencv.txt\n"
            f"Original error: {e}"
        ) from e
    return cv2


def _joint_keys() -> list[str]:
    return [
        "shoulder_pan",
        "shoulder_lift",
        "elbow_flex",
        "wrist_flex",
        "wrist_roll",
        "gripper",
    ]


def _obs_to_action(obs: dict) -> dict[str, float]:
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
    sys.stderr.write("\nSerial permission denied. Try: sudo chmod 666 %s or dialout group.\n\n" % port)


def _is_no_motors_on_bus_error(exc: BaseException) -> bool:
    s = str(exc)
    return "FeetechMotorsBus motor check failed" in s or "Missing motor IDs" in s


def _open_capture(cv2, camera: str) -> object:
    """Open V4L2 / OpenCV capture; ``camera`` is ``/dev/video0`` or an integer index string."""
    src: int | str
    if camera.isdigit():
        src = int(camera)
    else:
        src = camera
    cap = cv2.VideoCapture(src, cv2.CAP_V4L2)
    if not cap.isOpened():
        cap.release()
        cap = cv2.VideoCapture(src)
    if not cap.isOpened():
        raise SystemExit(f"Could not open camera: {camera}")
    return cap


def _largest_face_center(
    cv2,
    face_cascade,
    gray,
    *,
    min_neighbors: int,
    min_size: int,
) -> tuple[int, int] | None:
    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.08,
        minNeighbors=min_neighbors,
        minSize=(min_size, min_size),
    )
    if faces is None or len(faces) == 0:
        return None
    best = max(faces, key=lambda r: int(r[2]) * int(r[3]))
    x, y, w, h = (int(best[0]), int(best[1]), int(best[2]), int(best[3]))
    return x + w // 2, y + h // 2


def _clip(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Center the largest face using SO101 Follower (multi-joint visual servo)."
    )
    parser.add_argument("--camera", default="/dev/video0", help="OpenCV source: /dev/video0 or 0")
    parser.add_argument("--port", default="/dev/ttyACM0", help="Follower serial device")
    parser.add_argument("--robot-id", default="my_follower_arm", help="Follower calibration id")
    parser.add_argument(
        "--max-relative-target",
        type=float,
        default=32.0,
        help="LeRobot max_relative_target (deg); higher allows snappier combined joint steps",
    )
    # Vision smoothing / detection
    parser.add_argument(
        "--smooth",
        type=float,
        default=0.55,
        help="EMA weight on new face center (0..1); higher = faster tracking, lower = less jitter",
    )
    parser.add_argument(
        "--haar-min-neighbors",
        type=int,
        default=6,
        help="Haar minNeighbors (higher = fewer false positives, slightly slower lock)",
    )
    parser.add_argument(
        "--haar-min-size",
        type=int,
        default=56,
        help="Minimum face box size (px); reduces tiny-box jitter",
    )
    # Horizontal (pan + optional wrist roll trim)
    parser.add_argument(
        "--kp-pan",
        type=float,
        default=6.0,
        help="Proportional: pan deg per unit normalized horizontal error",
    )
    parser.add_argument(
        "--kd-x",
        type=float,
        default=2.5,
        help="Derivative on horizontal error (damp oscillation); scales (ex - ex_prev)",
    )
    parser.add_argument(
        "--max-step-pan",
        type=float,
        default=9.0,
        help="Max shoulder_pan delta per control tick (deg)",
    )
    parser.add_argument(
        "--wrist-roll-from-pan",
        type=float,
        default=0.22,
        help="wrist_roll increment as fraction of applied pan step (fine horizontal)",
    )
    parser.add_argument(
        "--max-step-wrist-roll",
        type=float,
        default=3.0,
        help="Cap absolute wrist_roll delta per tick (deg)",
    )
    # Vertical: one PD signal split across lift / elbow / wrist_flex
    parser.add_argument(
        "--kp-lift",
        type=float,
        default=5.0,
        help="Vertical P gain (deg per unit normalized y error) before split across joints",
    )
    parser.add_argument(
        "--kd-y",
        type=float,
        default=4.0,
        help="Vertical D gain on (ey - ey_prev) to reduce lift twitch",
    )
    parser.add_argument(
        "--max-step-lift",
        type=float,
        default=5.0,
        help="Max shoulder_lift delta per tick from vertical command (deg)",
    )
    parser.add_argument(
        "--elbow-from-lift",
        type=float,
        default=0.55,
        help="elbow_flex delta = this * clamped lift delta (same direction, coupled)",
    )
    parser.add_argument(
        "--max-step-elbow",
        type=float,
        default=4.5,
        help="Max elbow_flex delta per tick (deg)",
    )
    parser.add_argument(
        "--wrist-flex-from-lift",
        type=float,
        default=0.42,
        help="wrist_flex delta = this * clamped lift delta",
    )
    parser.add_argument(
        "--max-step-wrist-flex",
        type=float,
        default=3.5,
        help="Max wrist_flex delta per tick (deg)",
    )
    parser.add_argument(
        "--deadband-x",
        type=float,
        default=0.035,
        help="Ignore |normalized horizontal error| below this after smoothing",
    )
    parser.add_argument(
        "--deadband-y",
        type=float,
        default=0.045,
        help="Ignore |normalized vertical error| below this after smoothing",
    )
    parser.add_argument("--control-hz", type=float, default=22.0, help="Robot update rate (Hz)")
    parser.add_argument("--invert-pan", action="store_true", help="Flip horizontal (pan + roll trim)")
    parser.add_argument(
        "--invert-vertical",
        action="store_true",
        help="Flip shoulder_lift, elbow_flex, and wrist_flex together vs. vertical error",
    )
    parser.add_argument("--invert-wrist-roll", action="store_true", help="Flip wrist_roll trim sign")
    parser.add_argument("--max-offset-pan", type=float, default=55.0, help="Max |pan - baseline| (deg)")
    parser.add_argument("--max-offset-lift", type=float, default=38.0, help="Max |lift - baseline| (deg)")
    parser.add_argument("--max-offset-elbow", type=float, default=35.0, help="Max |elbow - baseline| (deg)")
    parser.add_argument("--max-offset-wrist-flex", type=float, default=28.0, help="Max |wrist_flex - baseline|")
    parser.add_argument("--max-offset-wrist-roll", type=float, default=22.0, help="Max |wrist_roll - baseline|")
    parser.add_argument(
        "--lost-return-frames",
        type=int,
        default=40,
        help="After this many frames without a face, ramp all joints toward baseline",
    )
    parser.add_argument(
        "--lost-smooth-decay",
        type=float,
        default=0.92,
        help="When face lost, EMA center drifts toward image center each frame (0..1)",
    )
    parser.add_argument("--no-preview", action="store_true", help="No GUI window")
    parser.add_argument("--dry-run", action="store_true", help="Camera + detection only; no robot")

    # Optional greeting motion on first face lock
    parser.add_argument(
        "--no-greet-on-first-face",
        action="store_true",
        help="Disable one-shot greeting gesture when first face is detected",
    )
    parser.add_argument(
        "--greet-recording",
        default="recordings/leader_poses_20260328_084430.json",
        help="Recording JSON used for greeting playback",
    )
    parser.add_argument(
        "--greet-key",
        default="greet",
        help="Action key inside recording JSON for the greeting gesture",
    )
    parser.add_argument(
        "--greet-home-action",
        default="idle",
        help="Recording key used as home pose while replaying greet",
    )
    parser.add_argument(
        "--greet-approach-max-deg",
        type=float,
        default=7.0,
        help="Per-step joint cap (deg) while approaching greet keyframes",
    )
    parser.add_argument(
        "--greet-approach-sleep",
        type=float,
        default=0.055,
        help="Sleep between approach steps during greet replay",
    )
    parser.add_argument(
        "--greet-tol-deg",
        type=float,
        default=3.5,
        help="Convergence tolerance (deg) for greet replay",
    )
    parser.add_argument(
        "--greet-time-scale",
        type=float,
        default=1.2,
        help="Trajectory time scale for greet playback (>1 slower)",
    )
    parser.add_argument(
        "--greet-hold-keyframe-s",
        type=float,
        default=1.0,
        help="Hold duration (s) if greet action is keyframe",
    )
    args = parser.parse_args()

    cv2 = _import_cv2()
    cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
    if not cascade_path.is_file():
        raise SystemExit(f"Haar cascade missing: {cascade_path}")
    face_cascade = cv2.CascadeClassifier(str(cascade_path))

    cap = _open_capture(cv2, args.camera)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 640)
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 480)
    cx0, cy0 = w * 0.5, h * 0.5
    smooth_fx, smooth_fy = cx0, cy0
    prev_ex = prev_ey = 0.0
    alpha = _clip(args.smooth, 0.05, 0.95)

    logger.info(
        "Camera %s (%dx%d) @ %.1f Hz | multi-joint vertical split | EMA=%.2f",
        args.camera,
        w,
        h,
        args.control_hz,
        alpha,
    )

    SO101Follower, SO101FollowerConfig = _import_robot()
    robot = None
    baseline: dict[str, float] | None = None
    lost_count = 0

    keys = {f"{k}.pos" for k in _joint_keys()}
    sp_key = "shoulder_pan.pos"
    sl_key = "shoulder_lift.pos"
    ef_key = "elbow_flex.pos"
    wf_key = "wrist_flex.pos"
    wr_key = "wrist_roll.pos"
    gp_key = "gripper.pos"

    # Greeting replay state (one-shot on first face lock by default)
    greet_enabled = not args.no_greet_on_first_face
    greet_done = not greet_enabled
    greet_block: dict | None = None
    greet_home: dict[str, float] | None = None

    if not args.dry_run:
        config = SO101FollowerConfig(
            port=args.port,
            id=args.robot_id,
            use_degrees=True,
            max_relative_target=float(args.max_relative_target),
            cameras={},
        )
        robot = SO101Follower(config)
        try:
            robot.connect(calibrate=False)
        except (ConnectionError, PermissionError, OSError) as e:
            if _is_serial_permission_error(e):
                _print_serial_permission_help(args.port)
            raise SystemExit(1) from e
        except RuntimeError as e:
            if _is_no_motors_on_bus_error(e):
                logger.error("No motors on bus; check USB port and follower power.")
            raise SystemExit(1) from e

        obs = robot.get_observation()
        baseline = _obs_to_action(obs)
        logger.info("Baseline pose (deg): %s", {k: round(v, 2) for k, v in baseline.items()})

        if greet_enabled:
            rec_path = Path(args.greet_recording).expanduser()
            if not rec_path.is_absolute():
                rec_path = (_REPO_ROOT / rec_path).resolve()
            else:
                rec_path = rec_path.resolve()
            try:
                data = load_recording(rec_path)
                actions = data.get("actions") or {}
                block = actions.get(args.greet_key)
                if block is None:
                    logger.warning("Greeting disabled: action key not found: %s", args.greet_key)
                    greet_done = True
                else:
                    greet_block = block
                    greet_home = resolve_home_pose(
                        data,
                        home_action=args.greet_home_action,
                        avg_frames=20,
                    )
                    logger.info(
                        "Greeting armed: key=%s recording=%s",
                        args.greet_key,
                        rec_path,
                    )
            except Exception as e:
                logger.warning("Greeting disabled: could not load recording (%s)", e)
                greet_done = True

    period = 1.0 / max(1.0, args.control_hz)
    decay = _clip(args.lost_smooth_decay, 0.0, 0.999)
    prev_track_ok = False

    try:
        while True:
            t0 = time.perf_counter()
            ok, frame = cap.read()
            if not ok or frame is None:
                logger.warning("Frame grab failed")
                time.sleep(0.05)
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            face_pt = _largest_face_center(
                cv2,
                face_cascade,
                gray,
                min_neighbors=max(3, args.haar_min_neighbors),
                min_size=max(40, args.haar_min_size),
            )

            if face_pt is not None:
                fx, fy = float(face_pt[0]), float(face_pt[1])
                smooth_fx = alpha * fx + (1.0 - alpha) * smooth_fx
                smooth_fy = alpha * fy + (1.0 - alpha) * smooth_fy
                lost_count = 0
            else:
                lost_count += 1
                smooth_fx = decay * smooth_fx + (1.0 - decay) * cx0
                smooth_fy = decay * smooth_fy + (1.0 - decay) * cy0

            ex = (smooth_fx - cx0) / max(cx0, 1.0)
            ey = (smooth_fy - cy0) / max(cy0, 1.0)
            if args.invert_pan:
                ex = -ex
            if args.invert_vertical:
                ey = -ey

            track_ok = face_pt is not None
            if track_ok and not prev_track_ok:
                prev_ex, prev_ey = ex, ey
            prev_track_ok = track_ok

            if args.dry_run:
                if face_pt:
                    logger.info(
                        "raw=(%d,%d) smooth=(%.0f,%.0f) err=(%.3f,%.3f)",
                        face_pt[0],
                        face_pt[1],
                        smooth_fx,
                        smooth_fy,
                        ex,
                        ey,
                    )
            elif robot is not None and baseline is not None:
                obs = robot.get_observation()
                cmd = _obs_to_action(obs)

                # First-face greeting: run one taught gesture, then continue tracking.
                if (
                    face_pt is not None
                    and (not greet_done)
                    and greet_block is not None
                    and greet_home is not None
                ):
                    logger.info("First face lock detected: replay greeting '%s'", args.greet_key)
                    try:
                        replay_one_action(
                            robot,
                            greet_home,
                            greet_block,
                            hold_keyframe_s=args.greet_hold_keyframe_s,
                            tol_deg=args.greet_tol_deg,
                            approach_max_deg=args.greet_approach_max_deg,
                            approach_sleep=args.greet_approach_sleep,
                            trajectory_time_scale=args.greet_time_scale,
                            log_every=0,
                            plateau_exit_after=120,
                        )
                    except Exception as e:
                        logger.warning("Greeting replay failed: %s", e)
                    finally:
                        greet_done = True
                        # Refresh baseline from current encoder state after greeting playback.
                        try:
                            baseline = _obs_to_action(robot.get_observation())
                        except Exception:
                            pass
                        smooth_fx, smooth_fy = float(face_pt[0]), float(face_pt[1])
                        ex = (smooth_fx - cx0) / max(cx0, 1.0)
                        ey = (smooth_fy - cy0) / max(cy0, 1.0)
                        if args.invert_pan:
                            ex = -ex
                        if args.invert_vertical:
                            ey = -ey
                        prev_ex, prev_ey = ex, ey
                        lost_count = 0
                    continue

                if face_pt is None and lost_count > args.lost_return_frames:
                    ret_step = 6.0
                    for key in keys:
                        if key == gp_key:
                            cmd[key] = baseline[key]
                            continue
                        cur, tgt = cmd[key], baseline[key]
                        delta = tgt - cur
                        if abs(delta) < 0.08:
                            cmd[key] = tgt
                        else:
                            cmd[key] = cur + _clip(delta, -ret_step, ret_step)
                else:
                    # Horizontal PD
                    if abs(ex) < args.deadband_x:
                        d_pan = 0.0
                    else:
                        d_pan = args.kp_pan * ex + args.kd_x * (ex - prev_ex)
                    prev_ex = ex
                    d_pan = _clip(d_pan, -args.max_step_pan, args.max_step_pan)

                    # Vertical PD → master lift increment, then split to elbow / wrist_flex
                    if abs(ey) < args.deadband_y:
                        d_lift = 0.0
                    else:
                        d_lift = args.kp_lift * ey + args.kd_y * (ey - prev_ey)
                    prev_ey = ey
                    d_lift = _clip(d_lift, -args.max_step_lift, args.max_step_lift)

                    d_elbow = _clip(
                        args.elbow_from_lift * d_lift,
                        -args.max_step_elbow,
                        args.max_step_elbow,
                    )
                    d_wflex = _clip(
                        args.wrist_flex_from_lift * d_lift,
                        -args.max_step_wrist_flex,
                        args.max_step_wrist_flex,
                    )

                    # Wrist roll: small coupled horizontal trim
                    sign_roll = -1.0 if args.invert_wrist_roll else 1.0
                    d_roll = sign_roll * args.wrist_roll_from_pan * d_pan
                    d_roll = _clip(d_roll, -args.max_step_wrist_roll, args.max_step_wrist_roll)

                    new_pan = _clip(
                        cmd[sp_key] + d_pan,
                        baseline[sp_key] - args.max_offset_pan,
                        baseline[sp_key] + args.max_offset_pan,
                    )
                    new_lift = _clip(
                        cmd[sl_key] + d_lift,
                        baseline[sl_key] - args.max_offset_lift,
                        baseline[sl_key] + args.max_offset_lift,
                    )
                    new_elbow = _clip(
                        cmd[ef_key] + d_elbow,
                        baseline[ef_key] - args.max_offset_elbow,
                        baseline[ef_key] + args.max_offset_elbow,
                    )
                    new_wflex = _clip(
                        cmd[wf_key] + d_wflex,
                        baseline[wf_key] - args.max_offset_wrist_flex,
                        baseline[wf_key] + args.max_offset_wrist_flex,
                    )
                    new_roll = _clip(
                        cmd[wr_key] + d_roll,
                        baseline[wr_key] - args.max_offset_wrist_roll,
                        baseline[wr_key] + args.max_offset_wrist_roll,
                    )

                    cmd[sp_key] = new_pan
                    cmd[sl_key] = new_lift
                    cmd[ef_key] = new_elbow
                    cmd[wf_key] = new_wflex
                    cmd[wr_key] = new_roll
                    cmd[gp_key] = baseline[gp_key]

                robot.send_action(cmd)

            if not args.no_preview:
                vis = frame.copy()
                cv2.drawMarker(
                    vis,
                    (int(cx0), int(cy0)),
                    (0, 255, 0),
                    markerType=cv2.MARKER_CROSS,
                    markerSize=20,
                    thickness=2,
                )
                cv2.circle(vis, (int(smooth_fx), int(smooth_fy)), 10, (255, 128, 0), 2)
                if face_pt:
                    cv2.rectangle(
                        vis,
                        (int(face_pt[0] - 4), int(face_pt[1] - 4)),
                        (int(face_pt[0] + 4), int(face_pt[1] + 4)),
                        (0, 165, 255),
                        2,
                    )
                cv2.putText(
                    vis,
                    f"sm err=({ex:.2f},{ey:.2f}) lost={lost_count} q=quit",
                    (8, 24),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (0, 255, 0),
                    1,
                    cv2.LINE_AA,
                )
                cv2.imshow("face_track_follower", vis)
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    break

            elapsed = time.perf_counter() - t0
            time.sleep(max(0.0, period - elapsed))

    except KeyboardInterrupt:
        logger.info("Interrupted.")
    finally:
        cap.release()
        if not args.no_preview:
            cv2.destroyAllWindows()
        if robot is not None and baseline is not None:
            try:
                logger.info("Returning to baseline…")
                robot.send_action(baseline)
                time.sleep(0.4)
            except Exception as e:
                logger.warning("Could not restore baseline: %s", e)
            robot.disconnect()


if __name__ == "__main__":
    main()
