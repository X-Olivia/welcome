# SO101 Arm Driver Guide

## 中文说明

### 1. 在本项目中的作用

在本项目中，SO101 机械臂承担的是地图导览系统之外的“实体交互层”。

- 它可以在人脸检测后主动跟随并打招呼。
- 它可以在网页生成路线后，用手势指向访客接下来应该前往的方向。
- 它可以回放预录制的动作，例如 `greet`、`idle`、`dance`、`wave_goodbye` 以及八个方向的指向动作。

网页前后端仍然是主要的导览与路线规划系统，机械臂不会替代导览逻辑，而是补充实体交互体验。

### 2. 运行环境与依赖

- 目标硬件：**SO-ARM101 / SO101**
- 机器人软件栈：**LeRobot**
- Python 环境：建议与 LeRobot 使用同一个环境，例如 `conda activate lerobot`
- 人脸跟踪额外需要 OpenCV：

```bash
pip install -r arm_driver/requirements-opencv.txt
```

运行本目录脚本前，请确保：

1. SO101 leader / follower 已完成标定。
2. 串口权限可正常访问。
3. LeRobot 运行环境已正确安装。

LeRobot 的安装、总线配置、电机设置与标定，请以官方文档为准：

- https://huggingface.co/docs/lerobot

### 3. 文件总览

| 文件 | 中文说明 |
|------|----------|
| `__init__.py` | 包级说明，标记录制、回放、守护、人脸跟踪与测试工具。 |
| `replay_engine.py` | 多个脚本共用的回放底层库。 |
| `arm_daemon.py` | 本地 HTTP 守护进程，接收 `action_key` 并触发机械臂动作。 |
| `record_leader_poses.py` | Leader 机械臂交互式录制工具。 |
| `replay_leader_poses.py` | 在 follower 机械臂上批量回放录制文件。 |
| `face_track_follower.py` | 基于 OpenCV 的人脸跟踪与视觉伺服。 |
| `test_so101_motion.py` | Follower 串口与小幅度动作冒烟测试。 |

### 4. 共享回放引擎

文件：`replay_engine.py`

这个模块是多个脚本共用的回放核心库，主要被以下脚本调用：

- `arm_daemon.py`
- `replay_leader_poses.py`
- `face_track_follower.py`

核心职责包括：

- `load_recording(path)` 读取 UTF-8 JSON 录制文件。
- `resolve_home_pose(...)` 从录制动作中解析 home 姿态。
- `step_toward_target(...)` 让机器人逐步逼近目标姿态。
- `replay_trajectory_segment(...)` 按指定 FPS 回放轨迹帧。
- `replay_one_action(...)` 负责播放单个动作块：
  - 先靠近动作首姿态
  - keyframe 则保持一段时间，trajectory 则播放整段轨迹
  - 最后回到 home

支持的动作类型：

- `keyframe`
- `trajectory`

### 5. 本地 HTTP 守护进程

文件：`arm_daemon.py`

从仓库根目录启动：

```bash
python arm_driver/arm_daemon.py
```

主要接口：

- `GET /health`
- `POST /v1/play`

请求体示例：

```json
{
  "action_key": "point_east"
}
```

行为说明：

- 动作成功进入队列时返回 `202`
- `action_key` 不存在时返回 `400`
- 守护进程未就绪时返回 `503`

常用环境变量：

| 变量 | 含义 |
|------|------|
| `ARM_DAEMON_HOST` | 绑定地址，默认 `127.0.0.1` |
| `ARM_DAEMON_PORT` | 绑定端口，默认 `8765` |
| `ARM_RECORDING_PATH` | 录制 JSON 路径 |
| `ARM_FOLLOWER_PORT` | follower 机械臂串口 |
| `ARM_ROBOT_ID` | follower 标定 id |
| `ARM_HOME_ACTION` | 作为 home 的动作键，默认 `idle` |
| `ARM_DAEMON_DRY_RUN` | 只加载 JSON，不连接真机 |
| `ARM_HOLD_KEYFRAME_S` | keyframe 保持时间 |
| `ARM_APPROACH_MAX_DEG` | 每步最大关节变化 |
| `ARM_TRAJECTORY_TIME_SCALE` | 轨迹时间缩放 |

### 6. Leader 录制

文件：`record_leader_poses.py`

这个脚本用于从 leader 机械臂录制姿态和轨迹，并保存为 JSON 文件。

典型输出文件：

```text
recordings/leader_poses_<UTC>.json
```

常用参数：

- `--port`
- `--leader-id`
- `--output`
- `--dry-run`
- `--keyframe-samples`
- `--trajectory-fps`
- `--trajectory-seconds`
- `--no-auto-calibrate`

默认动作菜单包括：

- `point_west`
- `point_east`
- `point_north`
- `point_south`
- `point_northwest`
- `point_northeast`
- `point_southwest`
- `point_southeast`
- `idle`
- `greet`
- `dance`
- `wave_goodbye`

### 7. Follower 回放

文件：`replay_leader_poses.py`

这个脚本连接 follower 机械臂，并按照录制文件中的动作顺序进行回放。

常用参数：

- `--port`
- `--robot-id`
- `--recording`
- `--home-action`
- `--actions`
- `--hold-keyframe-s`
- `--approach-max-deg`
- `--trajectory-time-scale`
- `--dry-run`

典型流程：

1. 连接 follower 机械臂。
2. 回到 home。
3. 按顺序回放指定动作。

### 8. 人脸跟踪演示

文件：`face_track_follower.py`

这个脚本使用 OpenCV 与 Haar 人脸检测，让 follower 机械臂进行视觉跟踪。

支持能力包括：

- 基于 V4L2 / OpenCV 的摄像头输入
- 平滑后的人脸检测结果
- pan / lift / elbow / wrist 联动控制
- 首次稳定锁脸时可选播放问候动作

典型用途：

- 在展区现场做实时跟脸演示
- 当访客靠近时触发一次 `greet`

### 9. 冒烟测试

文件：`test_so101_motion.py`

这是一个最小化的 follower 机械臂动作测试，用于检查：

- 串口是否可用
- 基本动作是否正常
- 电机是否在线

在录制或回放完整动作文件前，建议先跑这个测试。

### 10. 典型工作流

1. 在 leader 机械臂上录制动作。
2. 在 follower 机械臂上回放并验证。
3. 启动 `arm_daemon.py`。
4. 由后端调用 `POST /v1/play`。
5. 将机械臂用于问候、指路或导览互动。

### 11. 与网页导览系统的联动

机械臂目前是以 `action_key` 的方式与网页导览系统联动的。

- 后端先判断访客接下来应该朝哪个方向移动。
- 再把这个方向映射到 `point_north`、`point_southeast` 等机械臂动作键。
- 然后由后端调用本机守护进程触发回放。

这样协议保持简单清晰：

- 前端：路线生成与界面展示
- 后端：路线、语义理解、动作决策
- 机械臂守护进程：实体动作执行

### 12. 说明

- 本文档根据当前 `arm_driver/` 目录源码整理。
- 如果文档与代码行为不一致，以代码行为为准。

---

## English

### 1. Role In This Project

In this project, the SO101 arm is the physical interaction layer on top of the map-based campus guide.

- It can greet visitors after detecting and tracking a face.
- It can point toward the first walking direction after the route is generated on screen.
- It can replay pre-recorded gestures such as `greet`, `idle`, `dance`, `wave_goodbye`, and directional pointing actions.

The web frontend and backend remain the main route-planning system. The arm does not replace the guide logic. It extends the experience with physical motion.

### 2. Environment And Dependencies

- Target hardware: **SO-ARM101 / SO101**
- Robot software stack: **LeRobot**
- Python environment: recommended to use the same environment as LeRobot, for example `conda activate lerobot`
- Face tracking requires OpenCV:

```bash
pip install -r arm_driver/requirements-opencv.txt
```

Before running any script here, make sure:

1. The SO101 leader/follower arm is calibrated.
2. The serial port is accessible.
3. The LeRobot environment is installed correctly.

Please follow the official LeRobot documentation for setup, motor configuration, and calibration:

- https://huggingface.co/docs/lerobot

### 3. File Overview

| File | English Description |
|------|---------------------|
| `__init__.py` | Package note for recording, replay, daemon, face tracking, and test utilities. |
| `replay_engine.py` | Shared replay library used by multiple scripts. |
| `arm_daemon.py` | Local HTTP daemon that accepts `action_key` and replays arm motions. |
| `record_leader_poses.py` | Interactive recording tool for the leader arm. |
| `replay_leader_poses.py` | Replay a recorded file on the follower arm. |
| `face_track_follower.py` | Face tracking and visual servo control using OpenCV. |
| `test_so101_motion.py` | Small follower-arm smoke test. |

### 4. Shared Replay Engine

File: `replay_engine.py`

This module is the core replay library used by:

- `arm_daemon.py`
- `replay_leader_poses.py`
- `face_track_follower.py`

Key functions and responsibilities:

- `load_recording(path)` loads a UTF-8 JSON recording file.
- `resolve_home_pose(...)` extracts a home pose from a recording action.
- `step_toward_target(...)` moves the robot gradually toward a target pose.
- `replay_trajectory_segment(...)` replays trajectory frames at a target FPS.
- `replay_one_action(...)` handles one action block:
  - approach the first pose
  - hold a keyframe or replay a trajectory
  - return to home

Supported action kinds:

- `keyframe`
- `trajectory`

### 5. Local HTTP Daemon

File: `arm_daemon.py`

Start it from the repository root:

```bash
python arm_driver/arm_daemon.py
```

Main endpoints:

- `GET /health`
- `POST /v1/play`

Example request:

```json
{
  "action_key": "point_east"
}
```

Behavior:

- Returns `202` when the action is accepted into the queue
- Returns `400` if the `action_key` does not exist in the recording
- Returns `503` if the daemon is not ready

Useful environment variables:

| Variable | Meaning |
|----------|---------|
| `ARM_DAEMON_HOST` | Bind host, default `127.0.0.1` |
| `ARM_DAEMON_PORT` | Bind port, default `8765` |
| `ARM_RECORDING_PATH` | Path to the recording JSON |
| `ARM_FOLLOWER_PORT` | Serial port for follower arm |
| `ARM_ROBOT_ID` | Calibrated follower robot id |
| `ARM_HOME_ACTION` | Action used as home pose, default `idle` |
| `ARM_DAEMON_DRY_RUN` | Load JSON only, do not connect to hardware |
| `ARM_HOLD_KEYFRAME_S` | Hold duration for keyframes |
| `ARM_APPROACH_MAX_DEG` | Max per-step joint movement |
| `ARM_TRAJECTORY_TIME_SCALE` | Trajectory playback time scale |

### 6. Recording On Leader Arm

File: `record_leader_poses.py`

This script records poses and trajectories from the leader arm into a JSON file.

Typical output:

```text
recordings/leader_poses_<UTC>.json
```

Useful arguments:

- `--port`
- `--leader-id`
- `--output`
- `--dry-run`
- `--keyframe-samples`
- `--trajectory-fps`
- `--trajectory-seconds`
- `--no-auto-calibrate`

Default action menu includes:

- `point_west`
- `point_east`
- `point_north`
- `point_south`
- `point_northwest`
- `point_northeast`
- `point_southwest`
- `point_southeast`
- `idle`
- `greet`
- `dance`
- `wave_goodbye`

### 7. Replay On Follower Arm

File: `replay_leader_poses.py`

This script connects to the follower arm and replays actions from a recording file.

Common options:

- `--port`
- `--robot-id`
- `--recording`
- `--home-action`
- `--actions`
- `--hold-keyframe-s`
- `--approach-max-deg`
- `--trajectory-time-scale`
- `--dry-run`

Typical flow:

1. Connect to the follower arm.
2. Move to home.
3. Replay the selected actions in order.

### 8. Face Tracking Demo

File: `face_track_follower.py`

This script uses OpenCV and Haar face detection to make the follower arm visually track a person.

It supports:

- camera input from V4L2 / OpenCV
- smoothed face detection
- pan / lift / elbow / wrist coordination
- optional greeting motion on the first stable face lock

Typical optional use:

- use live face tracking during an exhibition
- trigger `greet` once when a visitor arrives

### 9. Smoke Test

File: `test_so101_motion.py`

This is a minimal follower-arm motion test for checking:

- serial connection
- basic motion
- motor availability

It is useful before recording or replaying a full action file.

### 10. Typical Workflow

1. Record gestures on the leader arm.
2. Replay and validate them on the follower arm.
3. Start `arm_daemon.py`.
4. Let the backend call `POST /v1/play`.
5. Use the arm for greeting, pointing, or guided interaction.

### 11. Integration With The Web Guide

The arm is currently integrated at the action-key level.

- The backend decides which direction the visitor should move toward.
- That direction is mapped to an arm action such as `point_north` or `point_southeast`.
- The backend then calls the local daemon.

This keeps the protocol simple:

- frontend: route generation and UI
- backend: routing, interpretation, action decision
- arm daemon: physical replay execution

### 12. Notes

- This document is derived from the current source code under `arm_driver/`.
- If the code and the document differ, the code is authoritative.
