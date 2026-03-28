#!/usr/bin/env python3
"""
Recording script for SO-101 robot arm.

Easily extensible to GUI (Gradio, Tkinter, PyQt, etc.)
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
class RecordConfig:
    # Robot
    robot_type: str = "so101_follower"
    robot_port: str = "/dev/ttyACM0"
    robot_id: str = "my_follower_arm"

    # Teleoperator
    teleop_type: str = "so101_leader"
    teleop_port: str = "/dev/ttyACM1"
    teleop_id: str = "my_leader_arm"

    # Dataset
    repo_id: str = "local/so101_dataset"
    single_task: str = "Pick and place object"
    num_episodes: int = 10
    fps: int = 30

    # Visualization
    display_data: bool = True

    # Resume existing dataset
    resume: bool = False

    # Push to HuggingFace Hub
    push_to_hub: bool = False

    # Cameras
    cameras: list[CameraConfig] = field(default_factory=list)

    def build_command(self) -> list[str]:
        cmd = [
            "lerobot-record",
            f"--robot.type={self.robot_type}",
            f"--robot.port={self.robot_port}",
            f"--robot.id={self.robot_id}",
            f"--teleop.type={self.teleop_type}",
            f"--teleop.port={self.teleop_port}",
            f"--teleop.id={self.teleop_id}",
            f"--dataset.repo_id={self.repo_id}",
            f"--dataset.single_task={self.single_task}",
            f"--dataset.num_episodes={self.num_episodes}",
            f"--dataset.fps={self.fps}",
            f"--display_data={str(self.display_data).lower()}",
            f"--resume={str(self.resume).lower()}",
            f"--dataset.push_to_hub={str(self.push_to_hub).lower()}",
        ]

        if self.cameras:
            cameras_yaml = "{ " + ", ".join(c.to_yaml() for c in self.cameras) + " }"
            cmd.append(f"--robot.cameras={cameras_yaml}")

        return cmd


def run_recording(config: RecordConfig):
    """Run the recording with given configuration."""
    cmd = config.build_command()

    print("Running command:")
    print(" \\\n    ".join(cmd))
    print()

    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\nRecording stopped.")
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        sys.exit(1)


# Default configuration
DEFAULT_CONFIG = RecordConfig(
    robot_port="/dev/ttyACM0",
    teleop_port="/dev/ttyACM1",
    repo_id="local/act_pick_place",
    num_episodes=10,
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

    parser = argparse.ArgumentParser(description="Record SO-101 demonstrations")
    parser.add_argument("--episodes", "-n", type=int, help="Number of episodes")
    parser.add_argument("--repo-id", "-r", help="Dataset repository ID")
    parser.add_argument("--task", "-t", help="Task description")
    parser.add_argument("--no-display", action="store_true", help="Disable visualization")
    parser.add_argument("--resume", action="store_true", help="Resume existing dataset")
    parser.add_argument("--dry-run", action="store_true", help="Print command without running")
    args = parser.parse_args()

    config = DEFAULT_CONFIG

    if args.episodes:
        config.num_episodes = args.episodes
    if args.repo_id:
        config.repo_id = args.repo_id
    if args.task:
        config.single_task = args.task
    if args.no_display:
        config.display_data = False
    if args.resume:
        config.resume = True

    if args.dry_run:
        print(" \\\n    ".join(config.build_command()))
    else:
        run_recording(config)
