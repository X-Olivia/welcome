#!/usr/bin/env python3
"""
用 OpenCV 摄像头检测人脸，SO101 follower 通过 **多关节协同**（pan、wrist_roll、lift、elbow、wrist_flex）
使人脸框内「眼部参考点」趋近画面中心（十字线）。

依赖：conda activate lerobot（可 import lerobot），并安装本目录 requirements.txt 中的 opencv-python。

示例：
  conda activate lerobot
  pip install -r camera/requirements.txt
  python camera/face_track_arm.py --camera /dev/video0 --robot-port /dev/ttyACM0

仅测摄像头、不连机械臂：
  python camera/face_track_arm.py --camera-only
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

# 必须在 import cv2 之前：减轻 conda 下 OpenCV Qt 后端刷屏的字体目录警告
os.environ.setdefault("QT_LOGGING_RULES", "*.debug=false;qt.qpa.*=false")
os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "0")

import cv2

try:
    cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_ERROR)
except (AttributeError, ValueError):
    pass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_camera_dir = os.path.dirname(os.path.abspath(__file__))
if _camera_dir not in sys.path:
    sys.path.insert(0, _camera_dir)
from tracking_joints import apply_centering_to_action

JOINT_KEYS = [
    "shoulder_pan",
    "shoulder_lift",
    "elbow_flex",
    "wrist_flex",
    "wrist_roll",
    "gripper",
]


def _import_robot():
    try:
        from lerobot.robots.so_follower import SO101Follower, SO101FollowerConfig
    except ImportError as e:
        raise SystemExit(
            "无法导入 lerobot。请先: conda activate lerobot\n"
            f"原始错误: {e}"
        ) from e
    return SO101Follower, SO101FollowerConfig


def _obs_to_action(obs: dict) -> dict[str, float]:
    return {f"{k}.pos": float(obs[f"{k}.pos"]) for k in JOINT_KEYS if f"{k}.pos" in obs}


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def main() -> None:
    p = argparse.ArgumentParser(description="人脸追踪 + SO101 机械臂（眼部参考点居中）")
    p.add_argument("--camera", default="/dev/video0", help="OpenCV 设备，如 /dev/video0 或 0")
    p.add_argument("--width", type=int, default=640)
    p.add_argument("--height", type=int, default=480)
    p.add_argument("--robot-port", default="/dev/ttyACM0", help="follower MotorBus 串口")
    p.add_argument(
        "--robot-id",
        default="my_awesome_follower_arm",
        help="与 ~/.cache/.../so_follower/<id>.json 一致",
    )
    p.add_argument(
        "--camera-only",
        action="store_true",
        help="只打开摄像头做人脸框显示，不连接机械臂",
    )
    p.add_argument(
        "--face-anchor-y",
        type=float,
        default=0.38,
        help="追踪目标在人脸框内的垂直位置：从框顶向下的比例，约 0.35~0.42 对应眼/鼻区域",
    )
    p.add_argument(
        "--max-pan-step",
        type=float,
        default=8.0,
        help="水平基准步长（度/帧，再乘 pan-gain），会分摊到 pan+wrist_roll",
    )
    p.add_argument(
        "--max-lift-step",
        type=float,
        default=9.0,
        help="垂直基准步长（度/帧，再乘 lift-gain），会分摊到 lift+elbow+wrist_flex",
    )
    p.add_argument(
        "--pan-gain",
        type=float,
        default=1.0,
        help="水平追踪增益",
    )
    p.add_argument(
        "--lift-gain",
        type=float,
        default=2.4,
        help="垂直追踪增益（默认大于 1，补偿人脸几何中心 ey 往往很小的问题）",
    )
    p.add_argument(
        "--dead-zone-h",
        type=float,
        default=0.06,
        help="水平归一化偏差死区",
    )
    p.add_argument(
        "--dead-zone-v",
        type=float,
        default=0.05,
        help="垂直归一化偏差死区（可略小于水平）",
    )
    p.add_argument(
        "--invert-pan",
        action="store_true",
        help="水平方向反向（装摄像头方向不一时可开）",
    )
    p.add_argument(
        "--invert-lift",
        action="store_true",
        help="垂直方向反向",
    )
    args = p.parse_args()

    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    face_cascade = cv2.CascadeClassifier(cascade_path)
    if face_cascade.empty():
        raise SystemExit(f"无法加载 Haar 模型: {cascade_path}")

    cam_path = args.camera
    try:
        cam_index = int(cam_path)
    except ValueError:
        cam_index = cam_path

    cap = cv2.VideoCapture(cam_index, cv2.CAP_V4L2)
    if not cap.isOpened():
        cap = cv2.VideoCapture(cam_index)
    if not cap.isOpened():
        raise SystemExit(f"无法打开摄像头: {args.camera}")

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)

    max_step = max(args.max_pan_step * args.pan_gain, args.max_lift_step * args.lift_gain)
    robot = None
    if not args.camera_only:
        SO101Follower, SO101FollowerConfig = _import_robot()
        cfg = SO101FollowerConfig(
            port=args.robot_port,
            id=args.robot_id,
            use_degrees=True,
            max_relative_target=max_step + 14.0,
        )
        robot = SO101Follower(cfg)
        logger.info("连接机械臂…")
        robot.connect(calibrate=False)

    logger.info("按 Q 或 Ctrl+C 退出；追踪目标为脸框内眼区参考点，使十字线对准该点")

    cx_frame = args.width / 2.0
    cy_frame = args.height / 2.0
    ay = _clamp(args.face_anchor_y, 0.15, 0.65)
    pan_sign = -1.0 if args.invert_pan else 1.0
    lift_sign = -1.0 if not args.invert_lift else 1.0

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                logger.warning("读取帧失败")
                break

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.equalizeHist(gray)
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.12, minNeighbors=5, minSize=(48, 48))

            if len(faces) > 0:
                x, y, fw, fh = max(faces, key=lambda f: f[2] * f[3])
                # 水平：脸宽中心；垂直：眼区参考点（比几何中心更偏高，ey 更明显）
                cx = x + fw / 2.0
                cy = y + ay * fh
                ex = (cx - cx_frame) / cx_frame
                ey = (cy - cy_frame) / cy_frame

                cv2.rectangle(frame, (x, y), (x + fw, y + fh), (0, 255, 0), 2)
                cv2.circle(frame, (int(cx), int(cy)), 7, (0, 255, 255), -1)
                cv2.putText(
                    frame,
                    "track",
                    (int(cx) + 8, int(cy)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 255, 255),
                    1,
                    cv2.LINE_AA,
                )

                if robot is not None:
                    obs = robot.get_observation()
                    action = _obs_to_action(obs)
                    if apply_centering_to_action(
                        action,
                        ex,
                        ey,
                        pan_sign=pan_sign,
                        lift_sign=lift_sign,
                        max_pan_step=args.max_pan_step,
                        max_lift_step=args.max_lift_step,
                        pan_gain=args.pan_gain,
                        lift_gain=args.lift_gain,
                        dead_zone_h=args.dead_zone_h,
                        dead_zone_v=args.dead_zone_v,
                    ):
                        robot.send_action(action)
            else:
                cv2.putText(
                    frame,
                    "No face",
                    (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.0,
                    (0, 0, 255),
                    2,
                )

            cv2.line(frame, (int(cx_frame), 0), (int(cx_frame), args.height), (80, 80, 80), 1)
            cv2.line(frame, (0, int(cy_frame)), (args.width, int(cy_frame)), (80, 80, 80), 1)
            cv2.imshow("face_track_arm (q=quit)", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    except KeyboardInterrupt:
        logger.info("中断退出")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        if robot is not None:
            robot.disconnect()
            logger.info("机械臂已断开")


if __name__ == "__main__":
    main()
