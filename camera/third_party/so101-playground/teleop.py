#!/usr/bin/env python3
"""
Teleoperation script for SO-101 robot arm.
"""

import subprocess
import sys
from dataclasses import dataclass, field


@dataclass
class CameraConfig:
    name: str
    type: str  # "opencv" or "intelrealsense"
    width: int = 640
    height: int = 480
    fps: int = 30
    # OpenCV specific
    index_or_path: int | str | None = None
    # RealSense specific
    serial_number_or_name: str | None = None
    use_depth: bool = False

    def to_yaml(self) -> str:
        if self.type == "opencv":
            return (
                f"{self.name}: {{type: opencv, index_or_path: {self.index_or_path}, "
                f"width: {self.width}, height: {self.height}, fps: {self.fps}}}"
            )
        elif self.type == "intelrealsense":
            depth_str = ", use_depth: true" if self.use_depth else ""
            return (
                f'{self.name}: {{type: intelrealsense, serial_number_or_name: "{self.serial_number_or_name}", '
                f"width: {self.width}, height: {self.height}, fps: {self.fps}{depth_str}}}"
            )
        raise ValueError(f"Unknown camera type: {self.type}")


@dataclass
class TeleopConfig:
    # Robot
    robot_type: str = "so101_follower"
    robot_port: str = "/dev/ttyACM0"
    robot_id: str = "my_follower_arm"

    # Teleoperator
    teleop_type: str = "so101_leader"
    teleop_port: str = "/dev/ttyACM1"
    teleop_id: str = "my_leader_arm"

    # Control
    fps: int = 60
    teleop_time_s: float | None = None  # None = run indefinitely

    # Visualization
    display_data: bool = True

    # Cameras
    cameras: list[CameraConfig] = field(default_factory=list)

    def build_command(self) -> list[str]:
        cmd = [
            "lerobot-teleoperate",
            f"--robot.type={self.robot_type}",
            f"--robot.port={self.robot_port}",
            f"--robot.id={self.robot_id}",
            f"--teleop.type={self.teleop_type}",
            f"--teleop.port={self.teleop_port}",
            f"--teleop.id={self.teleop_id}",
            f"--fps={self.fps}",
            f"--display_data={str(self.display_data).lower()}",
        ]

        if self.teleop_time_s is not None:
            cmd.append(f"--teleop_time_s={self.teleop_time_s}")

        if self.cameras:
            cameras_yaml = "{ " + ", ".join(c.to_yaml() for c in self.cameras) + " }"
            cmd.append(f"--robot.cameras={cameras_yaml}")

        return cmd


def run_teleop(config: TeleopConfig):
    """Run teleoperation with given configuration."""
    cmd = config.build_command()

    print("Running command:")
    print(" \\\n    ".join(cmd))
    print()

    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\nTeleoperation stopped.")
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        sys.exit(1)


# Default configuration
DEFAULT_CONFIG = TeleopConfig(
    robot_port="/dev/ttyACM0",
    teleop_port="/dev/ttyACM1",
    cameras=[
        CameraConfig(
            name="side",
            type="intelrealsense",
            serial_number_or_name="213622301205",
            width=640,
            height=480,
            fps=30,
        ),
        CameraConfig(
            name="overhead",
            type="opencv",
            index_or_path=0,
            width=640,
            height=480,
            fps=30,
        ),
        CameraConfig(
            name="wrist",
            type="opencv",
            index_or_path=2,
            width=640,
            height=480,
            fps=30,
        ),
    ],
)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Teleoperate SO-101 robot arm")
    parser.add_argument("--fps", type=int, help="Control loop FPS (default: 60)")
    parser.add_argument("--duration", "-d", type=float, help="Duration in seconds (default: indefinite)")
    parser.add_argument("--no-display", action="store_true", help="Disable visualization")
    parser.add_argument("--dry-run", action="store_true", help="Print command without running")
    args = parser.parse_args()

    config = DEFAULT_CONFIG

    if args.fps:
        config.fps = args.fps
    if args.duration:
        config.teleop_time_s = args.duration
    if args.no_display:
        config.display_data = False

    if args.dry_run:
        print(" \\\n    ".join(config.build_command()))
    else:
        run_teleop(config)
