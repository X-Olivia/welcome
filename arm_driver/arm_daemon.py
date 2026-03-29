#!/usr/bin/env python3
"""
Local HTTP daemon: play one ``action_key`` from a fixed leader recording JSON.

Invoked by the FastAPI app when ``ARM_DAEMON_URL`` is set (see ``arm_driver/README.md``).

Run (lerobot conda env)::

  conda activate lerobot
  cd /path/to/welcome && python arm_driver/arm_daemon.py

Environment (optional)::

  ARM_DAEMON_HOST          bind address (default 127.0.0.1)
  ARM_DAEMON_PORT          listen port (default 8765)
  ARM_RECORDING_PATH       path to JSON; default fixed file under recordings/, else newest leader_poses_*.json
  ARM_FOLLOWER_PORT        serial device (default /dev/ttyACM0)
  ARM_ROBOT_ID             follower calibration id (default my_follower_arm)
  ARM_HOME_ACTION          recording key used as home pose (default idle)
  ARM_DAEMON_DRY_RUN       if 1/true: load JSON only, no robot
  ARM_QUIET_CLAMP          if 1/true: filter LeRobot clamp WARNING spam

HTTP API::

  GET  /health
  POST /v1/play   JSON body: {"action_key": "point_north"}
"""

from __future__ import annotations

import json
import logging
import os
import queue
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

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

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("arm_daemon")

DEFAULT_RECORDING_REL = Path("recordings/leader_poses_20260328_084430.json")


def _latest_recording(recordings_dir: Path) -> Path:
    files = sorted(recordings_dir.glob("leader_poses_*.json"), key=lambda p: p.stat().st_mtime)
    if not files:
        raise FileNotFoundError(f"No leader_poses_*.json under: {recordings_dir}")
    return files[-1]


def _resolve_recording_path() -> Path:
    raw = (os.environ.get("ARM_RECORDING_PATH") or "").strip()
    if raw:
        p = Path(raw).expanduser()
        if not p.is_absolute():
            p = (_REPO_ROOT / p).resolve()
        else:
            p = p.resolve()
        if p.is_file():
            return p
        raise FileNotFoundError(f"ARM_RECORDING_PATH is not a file: {p}")
    preferred = (_REPO_ROOT / DEFAULT_RECORDING_REL).resolve()
    if preferred.is_file():
        return preferred
    return _latest_recording(_REPO_ROOT / "recordings").resolve()


class DaemonContext:
    """Loads recording, connects Follower (unless dry-run), owns playback queue + worker."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.recording_path = _resolve_recording_path()
        self.data: dict[str, Any] = load_recording(self.recording_path)
        self.actions: dict[str, Any] = dict(self.data.get("actions") or {})
        self.home: dict[str, float] | None = None
        self.robot: Any = None
        self.ready = False
        self.startup_error: str | None = None
        self.task_queue: queue.Queue[str] = queue.Queue()
        self._worker_started = False

        self.port = os.environ.get("ARM_FOLLOWER_PORT", "/dev/ttyACM0").strip() or "/dev/ttyACM0"
        self.robot_id = os.environ.get("ARM_ROBOT_ID", "my_follower_arm").strip() or "my_follower_arm"
        self.home_action = os.environ.get("ARM_HOME_ACTION", "idle").strip() or "idle"
        self.dry_run = os.environ.get("ARM_DAEMON_DRY_RUN", "").strip().lower() in ("1", "true", "yes")

        self.hold_keyframe_s = float(os.environ.get("ARM_HOLD_KEYFRAME_S", "1.5"))
        self.approach_max_deg = float(os.environ.get("ARM_APPROACH_MAX_DEG", "7.0"))
        self.approach_sleep = float(os.environ.get("ARM_APPROACH_SLEEP", "0.055"))
        self.trajectory_time_scale = float(os.environ.get("ARM_TRAJECTORY_TIME_SCALE", "1.5"))
        self.tol_deg = float(os.environ.get("ARM_TOL_DEG", "3.5"))
        self.plateau_exit_after = int(os.environ.get("ARM_PLATEAU_EXIT_AFTER", "160"))
        self.progress_every = int(os.environ.get("ARM_PROGRESS_EVERY", "120"))
        mr = os.environ.get("ARM_MAX_RELATIVE_TARGET", "").strip()
        self.max_relative_target = float(mr) if mr else max(12.0, self.approach_max_deg + 4.0)
        self.no_auto_calibrate = os.environ.get("ARM_NO_AUTO_CALIBRATE", "").strip().lower() in ("1", "true", "yes")

    def _init_hardware(self) -> None:
        if self.dry_run:
            self.home = resolve_home_pose(
                self.data,
                home_action=self.home_action,
                avg_frames=20,
            )
            self.ready = True
            logger.info(
                "DRY_RUN: loaded %s (%d actions), robot not connected",
                self.recording_path,
                len(self.actions),
            )
            return

        self.home = resolve_home_pose(
            self.data,
            home_action=self.home_action,
            avg_frames=20,
        )
        SO101Follower, SO101FollowerConfig = import_so101_follower()
        config = SO101FollowerConfig(
            port=self.port,
            id=self.robot_id,
            use_degrees=True,
            max_relative_target=self.max_relative_target,
            cameras={},
        )
        robot = SO101Follower(config)
        try:
            robot.connect(calibrate=not self.no_auto_calibrate)
        except Exception as e:
            if is_serial_permission_error(e):
                logger.error("Serial permission denied: %s", self.port)
            self.startup_error = str(e)
            logger.exception("Follower connect failed")
            try:
                robot.disconnect()
            except Exception:
                pass
            return

        if not robot.bus.calibration:
            try:
                robot.disconnect()
            except Exception:
                pass
            self.startup_error = "Follower has no calibration"
            logger.error(self.startup_error)
            return

        try:
            robot.bus.enable_torque()
            step_toward_target(
                robot,
                self.home,
                max_step_deg=self.approach_max_deg,
                tol_deg=self.tol_deg,
                sleep_s=self.approach_sleep,
                log_every=self.progress_every,
                plateau_exit_after=self.plateau_exit_after,
            )
            time.sleep(0.2)
        except Exception as e:
            self.startup_error = str(e)
            logger.exception("Failed to reach home pose")
            try:
                robot.disconnect()
            except Exception:
                pass
            return

        self.robot = robot
        self.ready = True
        logger.info("Arm ready, recording: %s", self.recording_path)

    def worker(self) -> None:
        while True:
            key = self.task_queue.get()
            try:
                self._play_key(key)
            except Exception:
                logger.exception("Playback failed: %s", key)
            finally:
                self.task_queue.task_done()

    def _play_key(self, key: str) -> None:
        if key not in self.actions:
            logger.warning("Unknown action_key in recording: %s", key)
            return
        block = self.actions[key]
        if self.dry_run or self.robot is None:
            zh = (block.get("label_zh")) or key
            logger.info("[DRY_RUN] would play: %s (%s)", zh, key)
            return
        assert self.home is not None
        zh = (block.get("label_zh")) or key
        logger.info("Playing: %s (%s)", zh, key)
        with self.lock:
            replay_one_action(
                self.robot,
                self.home,
                block,
                hold_keyframe_s=self.hold_keyframe_s,
                tol_deg=self.tol_deg,
                approach_max_deg=self.approach_max_deg,
                approach_sleep=self.approach_sleep,
                trajectory_time_scale=self.trajectory_time_scale,
                log_every=self.progress_every,
                plateau_exit_after=self.plateau_exit_after,
            )
        time.sleep(0.15)

    def start_worker(self) -> None:
        if self._worker_started:
            return
        self._worker_started = True
        threading.Thread(target=self.worker, name="arm-playback", daemon=True).start()

    def enqueue_play(self, key: str) -> tuple[bool, str]:
        if key not in self.actions:
            return False, f"unknown action_key: {key}"
        self.task_queue.put(key)
        return True, "queued"


CTX: DaemonContext | None = None


class ArmHTTPRequestHandler(BaseHTTPRequestHandler):
    server_version = "ArmDaemon/1.0"

    def log_message(self, fmt: str, *args: object) -> None:
        logger.debug("%s - %s", self.address_string(), fmt % args)

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path != "/health":
            self.send_error(404, "Not Found")
            return
        ctx = CTX
        if ctx is None:
            self._send_json(500, {"status": "error", "detail": "context not initialized"})
            return
        self._send_json(
            200,
            {
                "status": "ok" if ctx.ready else "degraded",
                "ready": ctx.ready,
                "recording": str(ctx.recording_path),
                "queue_depth": ctx.task_queue.qsize(),
                "dry_run": ctx.dry_run,
                "startup_error": ctx.startup_error,
            },
        )

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path != "/v1/play":
            self.send_error(404, "Not Found")
            return
        ctx = CTX
        if ctx is None:
            self._send_json(500, {"status": "error", "detail": "context not initialized"})
            return
        if not ctx.ready:
            self._send_json(
                503,
                {
                    "status": "unavailable",
                    "detail": ctx.startup_error or "daemon not ready",
                },
            )
            return
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length > 0 else b"{}"
        try:
            body = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            self._send_json(400, {"status": "error", "detail": "invalid JSON"})
            return
        key = body.get("action_key")
        if not isinstance(key, str) or not key.strip():
            self._send_json(400, {"status": "error", "detail": "missing action_key"})
            return
        key = key.strip()
        logger.info("POST /v1/play action_key=%s", key)
        ok, msg = ctx.enqueue_play(key)
        if not ok:
            self._send_json(400, {"status": "error", "detail": msg})
            return
        self._send_json(202, {"status": "accepted", "action_key": key})


def main() -> None:
    global CTX

    if os.environ.get("ARM_QUIET_CLAMP", "").strip().lower() in ("1", "true", "yes"):
        logging.getLogger().addFilter(SuppressLeRobotClampWarningFilter())

    host = os.environ.get("ARM_DAEMON_HOST", "127.0.0.1").strip() or "127.0.0.1"
    port = int(os.environ.get("ARM_DAEMON_PORT", "8765"))

    CTX = DaemonContext()
    CTX._init_hardware()
    CTX.start_worker()

    httpd = ThreadingHTTPServer((host, port), ArmHTTPRequestHandler)
    logger.info("Listening on http://%s:%d (GET /health, POST /v1/play)", host, port)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down…")
    finally:
        httpd.server_close()
        if CTX and CTX.robot is not None:
            try:
                CTX.robot.disconnect()
            except Exception:
                pass


if __name__ == "__main__":
    main()
