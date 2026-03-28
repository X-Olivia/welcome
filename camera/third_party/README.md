# 第三方参考仓库（可选 `git clone`）

与本项目 **SO-ARM101 + LeRobot follower** 相关、可本地拉源码阅读或对照的官方/开源仓库：

## 必用（通过 pip 即可，不必 clone）

| 项目 | 用途 | 安装 |
|------|------|------|
| [ultralytics/ultralytics](https://github.com/ultralytics/ultralytics) | YOLOv8 / Pose | `pip install ultralytics`（见 `../requirements-yolo.txt`） |
| [huggingface/lerobot](https://github.com/huggingface/lerobot) | SO101 驱动与标定 | 你本机已有 `~/lerobot` 或 `pip install lerobot` |

## 可选浅克隆（只读参考）

在 `camera/third_party` 下执行：

```bash
bash camera/scripts/clone_reference_repos.sh
```

会浅克隆 **Ultralytics** 源码，便于查 API；**不会**拉取完整 lerobot（体积大，请继续用你已有的 `~/lerobot`）。

## 其它社区项目（按需自行 clone）

- [AIDASLab/lerobot-so101-bimanual](https://github.com/AIDASLab/lerobot-so101-bimanual) — 双臂 SO101 相关实验  
- [preespp/augment-robot-arm-yolo-vla](https://github.com/preespp/augment-robot-arm-yolo-vla) — YOLO 与机械臂 VLA 方向（星数少，作思路参考）

本项目 **`yolo_track_arm.py`** 使用官方 **Ultralytics YOLOv8-Pose**，与具体 SO101 型号通过 **LeRobot 串口层** 对接，不依赖上述仓库的代码树。
