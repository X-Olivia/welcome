#!/usr/bin/env python3
"""
SO-ARM101（LeRobot so101_follower）连通性与小幅动作测试。

前置（官方文档）：
  - 已用 `lerobot-setup-motors` 配置电机 ID 与波特率
  - 已用 `lerobot-calibrate` 生成标定（与本脚本 `--robot-id` 一致）
  - Linux 串口权限：例如 `sudo chmod 666 /dev/ttyACM0` 或将用户加入 dialout/uucp

用法（在已安装 lerobot 的 conda 环境中）：
  conda activate lerobot
  cd /path/to/welcome
  python arm_driver/test_so101_motion.py --port /dev/ttyACM0

仅检查能否 import lerobot、不连接硬件：
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
            "无法导入 lerobot（SO101Follower）。请在 conda 环境 `lerobot` 中安装：\n"
            "  pip install 'lerobot[feetech]'\n"
            "或按官方文档从源码 editable 安装。\n"
            f"原始错误: {e}"
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
    """将观测中的 *.pos 转为 send_action 所需格式（已是目标关节角）。"""
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
        "\n无法打开串口（权限不足）。在 Ubuntu/Debian 上常见解决办法：\n\n"
        "  1) 临时：sudo chmod 666 " + port + "\n"
        "  2) 永久：将当前用户加入 dialout 组后重新登录（或注销再登录）\n"
        "       sudo usermod -aG dialout \"$USER\"\n"
        "       groups   # 确认输出里有 dialout\n\n"
        "然后重新运行本脚本。\n"
    )


def _is_no_motors_on_bus_error(exc: BaseException) -> bool:
    s = str(exc)
    return "FeetechMotorsBus motor check failed" in s or "Missing motor IDs" in s


def _print_motor_bus_help(port: str) -> None:
    sys.stderr.write(
        "\n串口已打开，但总线上未扫描到任何电机（found motor list 为空）。"
        "这是接线/电源/端口选择问题，不是 Python 脚本本身错误。\n\n"
        "请逐项检查：\n"
        "  • 机械臂控制板是否已 **USB 接到电脑**，且 **电源已供电**。\n"
        "  • USB 是否插在 **follower（从臂）** 控制板上；leader 与 follower 各有一个串口时，"
        "请用官方工具确认端口：\n"
        "      lerobot-find-port\n"
        "    若有 /dev/ttyACM0 与 /dev/ttyACM1，可尝试把 --port 改成另一个。\n"
        "  • 3-pin 舵机总线是否从控制板接到第一节电机，整条串联完好。\n"
        "  • 新装电机需先配置 ID 与波特率（官方文档）：\n"
        "      lerobot-setup-motors --robot.type=so101_follower --robot.port=" + port + "\n"
        "  • 部分 Waveshare 控制板要求 USB 通道跳线在 **B** 侧（见 LeRobot SO-101 文档）。\n\n"
        "排除后重新运行本脚本。\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="SO-ARM101 串口运动测试（LeRobot）")
    parser.add_argument("--port", default="/dev/ttyACM0", help="MotorBus 串口设备")
    parser.add_argument(
        "--robot-id",
        default="my_awesome_follower_arm",
        help=(
            "与标定 JSON 文件名一致（不含 .json），通常在 "
            "~/.cache/huggingface/lerobot/calibration/robots/so_follower/"
        ),
    )
    parser.add_argument(
        "--shoulder-delta-deg",
        type=float,
        default=12.0,
        help="在当前 shoulder_pan 基础上转动的角度（度），负值反向",
    )
    parser.add_argument(
        "--hold-seconds",
        type=float,
        default=2.0,
        help="到达目标后保持秒数再复原",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只检查 import，不连接串口",
    )
    args = parser.parse_args()

    SO101Follower, SO101FollowerConfig = _import_robot()

    if args.dry_run:
        logger.info("dry-run: lerobot SO101Follower 导入成功。")
        sys.exit(0)

    # 限制单步相对幅度，降低误动作风险（与官方 SOFollower 配置一致，单位：度）
    config = SO101FollowerConfig(
        port=args.port,
        id=args.robot_id,
        use_degrees=True,
        max_relative_target=30.0,
    )
    robot = SO101Follower(config)

    logger.info("连接机械臂（不触发交互式标定；若从未标定请先运行 lerobot-calibrate）…")
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
        logger.info("当前关节目标基线（度）: %s", {k: round(v, 2) for k, v in base.items()})

        moved = dict(base)
        sp = "shoulder_pan.pos"
        moved[sp] = float(moved[sp]) + args.shoulder_delta_deg

        logger.info("发送动作：shoulder_pan %+s°", args.shoulder_delta_deg)
        sent = robot.send_action(moved)
        logger.info("已发送（可能被安全裁剪）: shoulder_pan=%s", sent.get(sp))
        time.sleep(args.hold_seconds)

        logger.info("回到起始姿态…")
        robot.send_action(base)
        time.sleep(1.0)
        logger.info("测试完成。")
    finally:
        robot.disconnect()


if __name__ == "__main__":
    main()
