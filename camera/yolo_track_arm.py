#!/usr/bin/env python3
"""
YOLOv8-Pose（Ultralytics）检测人体关键点，用鼻/双眼中点作为追踪目标；
SO101 **多关节**（pan、wrist_roll、lift、elbow、wrist_flex）协同使 target 居中。

默认用 Matplotlib 显示，避免 conda 下 OpenCV Qt 字体刷屏；需要 OpenCV 窗口可加 --viz opencv。

  conda activate lerobot
  pip install -r camera/requirements.txt -r camera/requirements-yolo.txt
  python camera/yolo_track_arm.py --camera /dev/video0

参考源码可 git clone（见 camera/third_party/README.md）。
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

os.environ.setdefault("QT_LOGGING_RULES", "*.debug=false;qt.qpa.*=false")

_camera_dir = os.path.dirname(os.path.abspath(__file__))
if _camera_dir not in sys.path:
    sys.path.insert(0, _camera_dir)
from tracking_joints import apply_centering_to_action

import cv2
import numpy as np

try:
    cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_ERROR)
except (AttributeError, ValueError):
    pass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

JOINT_KEYS = [
    "shoulder_pan",
    "shoulder_lift",
    "elbow_flex",
    "wrist_flex",
    "wrist_roll",
    "gripper",
]

# COCO 17 点：0 鼻, 1 左眼, 2 右眼
KPT_NOSE, KPT_LEYE, KPT_REYE = 0, 1, 2


def _import_robot():
    try:
        from lerobot.robots.so_follower import SO101Follower, SO101FollowerConfig
    except ImportError as e:
        raise SystemExit(
            "无法导入 lerobot。请先: conda activate lerobot\n"
            f"原始错误: {e}"
        ) from e
    return SO101Follower, SO101FollowerConfig


def _import_yolo():
    try:
        from ultralytics import YOLO
    except ImportError as e:
        raise SystemExit(
            "请安装: pip install -r camera/requirements-yolo.txt\n"
            f"原始错误: {e}"
        ) from e
    return YOLO


def _obs_to_action(obs: dict) -> dict[str, float]:
    return {f"{k}.pos": float(obs[f"{k}.pos"]) for k in JOINT_KEYS if f"{k}.pos" in obs}


def _pick_target_from_pose(
    keypoints_xy,  # (17, 2) float tensor or ndarray
    keypoints_conf,  # (17,) optional
    box_xyxy,
    conf_th: float,
) -> tuple[float, float] | None:
    """返回追踪点 (cx, cy) 像素坐标；优先双眼中点，其次鼻，其次框内上 1/3。"""
    kp = keypoints_xy
    if hasattr(kp, "cpu"):
        kp = kp.cpu().numpy()
    else:
        kp = np.asarray(kp)
    conf = None
    if keypoints_conf is not None:
        conf = keypoints_conf
        if hasattr(conf, "cpu"):
            conf = conf.cpu().numpy()
        else:
            conf = np.asarray(conf)

    def ok(i: int) -> bool:
        if conf is None:
            return kp[i, 0] > 1 and kp[i, 1] > 1
        return float(conf[i]) >= conf_th

    bx1, by1, bx2, by2 = [float(x) for x in box_xyxy[:4]]
    bw, bh = bx2 - bx1, by2 - by1

    if ok(KPT_LEYE) and ok(KPT_REYE):
        cx = (float(kp[KPT_LEYE, 0]) + float(kp[KPT_REYE, 0])) / 2.0
        cy = (float(kp[KPT_LEYE, 1]) + float(kp[KPT_REYE, 1])) / 2.0
        return cx, cy
    if ok(KPT_NOSE):
        return float(kp[KPT_NOSE, 0]), float(kp[KPT_NOSE, 1])
    # 回退：人体框上部中心（头肩）
    return bx1 + bw / 2.0, by1 + bh * 0.25


def main() -> None:
    p = argparse.ArgumentParser(description="YOLOv8-Pose 人体关键点追踪 + SO101")
    p.add_argument("--camera", default="/dev/video0")
    p.add_argument("--width", type=int, default=640)
    p.add_argument("--height", type=int, default=480)
    p.add_argument("--robot-port", default="/dev/ttyACM0")
    p.add_argument("--robot-id", default="my_awesome_follower_arm")
    p.add_argument("--camera-only", action="store_true")
    p.add_argument(
        "--model",
        default="yolov8n-pose.pt",
        help="Ultralytics Pose 权重，首次运行自动下载",
    )
    p.add_argument("--kpt-conf", type=float, default=0.35, help="关键点置信度阈值")
    p.add_argument("--max-pan-step", type=float, default=8.0, help="水平基准步长（度/帧）")
    p.add_argument("--max-lift-step", type=float, default=9.0, help="垂直基准步长（度/帧）")
    p.add_argument("--pan-gain", type=float, default=1.0)
    p.add_argument("--lift-gain", type=float, default=2.4)
    p.add_argument("--dead-zone-h", type=float, default=0.06)
    p.add_argument("--dead-zone-v", type=float, default=0.05)
    p.add_argument("--invert-pan", action="store_true")
    p.add_argument("--invert-lift", action="store_true")
    p.add_argument(
        "--viz",
        choices=("matplotlib", "opencv"),
        default="matplotlib",
        help="matplotlib 可避免 OpenCV+Qt 字体警告；opencv 用传统窗口",
    )
    args = p.parse_args()

    YOLO = _import_yolo()
    logger.info("加载 YOLO: %s", args.model)
    model = YOLO(args.model)

    try:
        cam_index = int(args.camera)
    except ValueError:
        cam_index = args.camera

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

    cx_frame = args.width / 2.0
    cy_frame = args.height / 2.0
    pan_sign = -1.0 if args.invert_pan else 1.0
    lift_sign = -1.0 if not args.invert_lift else 1.0

    mpl_im = None
    fig = ax = None
    if args.viz == "matplotlib":
        import matplotlib.pyplot as plt

        plt.ion()
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.set_axis_off()
        try:
            fig.canvas.manager.set_window_title("yolo_track_arm (close window to quit)")
        except (AttributeError, TypeError):
            pass

    logger.info("按 Q（OpenCV）或关闭窗口（Matplotlib）退出")

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break

            results = model(frame, verbose=False, imgsz=640)
            r0 = results[0]

            target = None
            if r0.boxes is not None and len(r0.boxes) > 0:
                xyxy = r0.boxes.xyxy
                areas = (xyxy[:, 2] - xyxy[:, 0]) * (xyxy[:, 3] - xyxy[:, 1])
                idx = int(areas.argmax())
                if r0.keypoints is not None and r0.keypoints.xy is not None:
                    n = int(r0.keypoints.xy.shape[0])
                    if n > idx:
                        kp_xy = r0.keypoints.xy[idx]
                        kp_conf = (
                            r0.keypoints.conf[idx]
                            if r0.keypoints.conf is not None and r0.keypoints.conf.shape[0] > idx
                            else None
                        )
                        target = _pick_target_from_pose(
                            kp_xy, kp_conf, xyxy[idx], args.kpt_conf
                        )
                if target is None:
                    bx1, by1, bx2, by2 = [float(x) for x in xyxy[idx]]
                    target = (bx1 + bx2) / 2.0, by1 + (by2 - by1) * 0.22

            if target is not None:
                cx, cy = target
                ex = (cx - cx_frame) / cx_frame
                ey = (cy - cy_frame) / cy_frame
                cv2.circle(frame, (int(cx), int(cy)), 8, (0, 255, 255), -1)
                cv2.putText(
                    frame,
                    "target",
                    (int(cx) + 6, int(cy)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 255, 0),
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
                    "no person/pose",
                    (16, 36),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.9,
                    (0, 0, 255),
                    2,
                )

            cv2.line(
                frame,
                (int(cx_frame), 0),
                (int(cx_frame), args.height),
                (80, 80, 80),
                1,
            )
            cv2.line(
                frame,
                (0, int(cy_frame)),
                (args.width, int(cy_frame)),
                (80, 80, 80),
                1,
            )

            if args.viz == "opencv":
                cv2.imshow("yolo_track_arm (q=quit)", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
            else:
                import matplotlib.pyplot as plt

                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                if ax is not None:
                    if mpl_im is None:
                        mpl_im = ax.imshow(rgb)
                    else:
                        mpl_im.set_data(rgb)
                fig.canvas.draw_idle()
                fig.canvas.flush_events()
                plt.pause(0.001)
                if not plt.fignum_exists(fig.number):
                    break
    except KeyboardInterrupt:
        logger.info("中断退出")
    finally:
        cap.release()
        if args.viz == "opencv":
            cv2.destroyAllWindows()
        if args.viz == "matplotlib" and fig is not None:
            import matplotlib.pyplot as plt

            plt.close(fig)
        if robot is not None:
            robot.disconnect()
            logger.info("机械臂已断开")


if __name__ == "__main__":
    main()
