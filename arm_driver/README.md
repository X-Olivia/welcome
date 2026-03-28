# arm_driver

## 仅 follower（无 leader）

本项目与 `test_so101_motion.py` **只连接 `so101_follower`**，不依赖 leader。没有 leader 时照样可以：给从臂上电、USB 接 follower 控制板、用标定好的 `robot-id` 跑测试或后续接入后端。

官方文档里若出现 `so101_leader`、`lerobot-teleoperate` 双机，属于遥操作/数据采集场景；开放日「固定装置指方向」用代码发预设姿态即可，无需 leader。

## 与后端的关系

`backend/app/services/arm.py` 在 **`ARM_MOCK=true`（默认）** 时**不会**向真机发指令，只打日志。接入硬件后可将 `execute_arm_action` 改为调用本目录脚本或通过 HTTP 调独立进程。

## SO-ARM101 真机测试脚本

```bash
conda activate lerobot
cd /path/to/welcome
python arm_driver/test_so101_motion.py --port /dev/ttyACM0
```

`--robot-id` 必须与本地标定文件名一致，例如：

`~/.cache/huggingface/lerobot/calibration/robots/so_follower/<id>.json`

本机若已有 `my_awesome_follower_arm.json`，则使用默认 `--robot-id my_awesome_follower_arm`（可 `ls` 该目录确认）。若你用别的名字跑过 `lerobot-calibrate`，把 `--robot-id` 改成对应名字即可。

若出现 **`Missing motor IDs` / `found motor list: {}`**：串口能打开，但 **Feetech 总线上没有扫到电机**。请检查 follower 是否上电、USB 是否接在 **从臂** 控制板、线序是否接好；多路 `ttyACM*` 时用 **`lerobot-find-port`** 确认端口或换试 `/dev/ttyACM1`；新电机需先运行 **`lerobot-setup-motors --robot.type=so101_follower --robot.port=...`**。

若出现 **`Permission denied: '/dev/ttyACM0'`**，说明当前用户对串口没有读写权限，任选其一：

- **推荐（永久）**：`sudo usermod -aG dialout "$USER"`，然后**注销并重新登录**（或重启），再执行 `groups` 确认含有 `dialout`。
- **临时**：`sudo chmod 666 /dev/ttyACM0`（拔插 USB 后可能需重来）。

仅检查能否导入 `lerobot`：

```bash
python arm_driver/test_so101_motion.py --dry-run
```

脚本会连接 `so101_follower`，读取当前关节角，令 **shoulder_pan** 转动约 12°，保持数秒后复原。请先完成官方 **`lerobot-setup-motors`** 与 **`lerobot-calibrate`**，且 `--robot-id` 与标定时一致。

日后可将 `ArmAction` 映射为关节目标或示教轨迹，再用 `lerobot` 的 `send_action` 执行。
