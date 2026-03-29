# 机械臂模块说明 · Arm integration (SO-ARM101)

---

## 中文

### 功能概览

本目录实现 **SO-ARM101**（LeRobot `so101_leader` / `so101_follower`）与校园导览系统的衔接，主要包括：

| 能力 | 说明 |
|------|------|
| **示教录制** | 在 **Leader** 臂上录制关节快照或短时轨迹，导出统一 JSON（`recordings/leader_poses_*.json`）。 |
| **离线回放** | 在 **Follower** 臂上按 JSON 播放：先平滑回 `home`（默认取录制中的 `idle`），再执行每个动作并回到 `home`。 |
| **连通性测试** | 小幅度转动 `shoulder_pan`，验证串口、标定与总线。 |
| **HTTP 守护进程** | 本机监听端口，按 `action_key` 播放录制中的单段动作；供 FastAPI 在路线生成后异步调用。 |
| **Web 后端联动** | 路线折线首段方向映射为八个罗盘向的 `action_key`，通过 `ARM_DAEMON_URL` 通知守护进程（可选）。 |
| **人脸居中跟踪** | OpenCV + Haar；EMA 平滑 + PD；竖直指令分配至 `shoulder_lift` / `elbow_flex` / `wrist_flex`，水平含 `shoulder_pan` 与小幅 `wrist_roll`（勿与 `arm_daemon` 同占串口）。 |

### 文件一览

| 文件 | 作用 |
|------|------|
| `record_leader_poses.py` | 连接 Leader，交互式录制多类动作到 JSON。 |
| `replay_engine.py` | 回放核心：读 JSON、`step_toward_target` 平滑逼近、`replay_one_action` 执行 keyframe/trajectory。 |
| `replay_leader_poses.py` | CLI：在 Follower 上顺序播放整个录制文件。 |
| `arm_daemon.py` | 常驻进程：`GET /health`、`POST /v1/play`，队列串行播放，独占串口。 |
| `face_track_follower.py` | 摄像头人脸跟踪：多关节（pan/lift/elbow/wrist）视觉伺服使人脸居中（需 `requirements-opencv.txt`）。 |
| `requirements-opencv.txt` | 可选依赖：`opencv-python`（人脸脚本用）。 |
| `test_so101_motion.py` | Follower 小幅动作自检。 |
| `__init__.py` | 包标记，便于 `arm_driver.*` 导入。 |

### 与仓库其余部分的关系

- **后端**（`backend/app/services/`）：`arm.py`（逻辑动作 + mock）、`route_arm_direction.py`（折线→八向 key）、`arm_daemon_client.py`（HTTP 通知守护进程）；`routes.py` 在 `/api/guide`、`/api/route*` 成功规划路线后可选触发守护进程。
- **配置**：`backend/.env` 中 `ARM_DAEMON_URL`、`ARM_MAP_NORTH_OFFSET_DEG`、`ARM_MOCK` 等（详见 `backend/.env.example`）。

### 典型运行顺序（现场演示）

1. （可选）`conda activate lerobot`，用 `record_leader_poses.py` 在 Leader 上录制并保存 JSON。  
2. 将板子接到 **Follower**，完成 `lerobot-calibrate`（与 `--robot-id` 一致）。  
3. 启动守护进程：`python arm_driver/arm_daemon.py`（可用 `ARM_DAEMON_DRY_RUN=1` 调试 HTTP）。  
4. 启动后端并设置 `ARM_DAEMON_URL=http://127.0.0.1:8765`，前端生成路线后即可触发对应方向的示教动作。  
5. （可选）**人脸跟踪**：先停掉 `arm_daemon`，再 `pip install -r arm_driver/requirements-opencv.txt`，执行  
   `python arm_driver/face_track_follower.py --camera /dev/video0 --port /dev/ttyACM0`。
   默认首次识别人脸会先回放 `greet` 动作，再继续跟踪；可用 `--no-greet-on-first-face` 关闭。
   左右反加 `--invert-pan`；整条竖直链反加 `--invert-vertical`。

环境变量与 API 细节见各脚本顶部 **module docstring**。

---

## English

### Feature overview

This package integrates the **SO-ARM101** arm (LeRobot `so101_leader` / `so101_follower`) with the campus guide stack:

| Capability | Description |
|------------|-------------|
| **Tele-op recording** | On the **Leader** arm, record joint keyframes or short trajectories into a single JSON file under `recordings/`. |
| **Offline replay** | On the **Follower**, play that JSON: smooth approach to `home` (default: `idle` entry), run each action, return to `home`. |
| **Smoke test** | Nudge `shoulder_pan` to verify USB bus, calibration, and torque. |
| **HTTP daemon** | Local server: play one `action_key` at a time from the loaded recording; invoked by FastAPI after a route is planned. |
| **Backend bridge** | Maps the first meaningful segment of the route polyline to an 8-way compass key (`point_north`, …) and `POST`s to the daemon when `ARM_DAEMON_URL` is set. |
| **Face centering** | OpenCV + Haar; EMA + PD; vertical command split across `shoulder_lift`, `elbow_flex`, `wrist_flex`; horizontal uses `shoulder_pan` plus small `wrist_roll` (no serial sharing with `arm_daemon`). |

### File map

| File | Role |
|------|------|
| `record_leader_poses.py` | Connect Leader; interactive menu to record named actions to JSON. |
| `replay_engine.py` | Shared replay logic: load JSON, ramped `step_toward_target`, `replay_one_action` for `keyframe` / `trajectory` blocks. |
| `replay_leader_poses.py` | CLI: play a full recording file on Follower in order. |
| `arm_daemon.py` | Long-running process: `GET /health`, `POST /v1/play`, queued playback, single serial owner. |
| `face_track_follower.py` | Camera face tracking: multi-joint servo (pan/lift/elbow/wrist) to center the face. |
| `requirements-opencv.txt` | Optional: `opencv-python` for the face script. |
| `test_so101_motion.py` | Minimal Follower motion sanity check. |
| `__init__.py` | Package marker for `arm_driver.*` imports. |

### Relation to the rest of the repo

- **Backend** (`backend/app/services/`): `arm.py` (logical `ArmAction` + mock), `route_arm_direction.py` (polyline → 8-way key), `arm_daemon_client.py` (non-blocking HTTP to daemon); `routes.py` optionally triggers the daemon after successful `/api/guide` and `/api/route*`.
- **Configuration**: `ARM_DAEMON_URL`, `ARM_MAP_NORTH_OFFSET_DEG`, `ARM_MOCK`, etc. in `backend/.env` (see `backend/.env.example`).

### Typical demo flow

1. (Optional) Record on Leader with `record_leader_poses.py`.  
2. Move the board to **Follower**; run `lerobot-calibrate` matching `--robot-id`.  
3. Start `python arm_driver/arm_daemon.py` (use `ARM_DAEMON_DRY_RUN=1` to test HTTP only).  
4. Run the API with `ARM_DAEMON_URL=http://127.0.0.1:8765`; planning a route from the UI queues the matching directional pose.  
5. (Optional) **Face tracking**: stop `arm_daemon`, `pip install -r arm_driver/requirements-opencv.txt`, then  
   `python arm_driver/face_track_follower.py --camera /dev/video0 --port /dev/ttyACM0`.
   By default, the first stable face lock triggers one `greet` replay, then tracking resumes.
   Use `--no-greet-on-first-face` to disable. Use `--invert-pan` / `--invert-vertical` if axes are reversed.

Full env var and HTTP API lists are in each script’s **module docstring** (English in source).

---

## Dependencies

- **Conda env** with LeRobot and Feetech stack (see project root `README.md`).  
- **Linux**: serial permissions (`dialout` or `chmod` on `/dev/ttyACM*`).
- **Face tracking**: `pip install -r arm_driver/requirements-opencv.txt` in the same env.

---

## Code comments

Source files under `arm_driver/` and the backend arm-related modules use **English** docstrings and comments for review and submission; interactive prompts in `record_leader_poses.py` may remain Chinese for operator convenience.
