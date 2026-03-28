# 摄像头人脸追踪 + SO101 follower

独立小工具：通过 **LeRobot `so101_follower`** 多关节协同（水平：pan + wrist_roll；垂直：lift + elbow + wrist_flex）使 target 趋向画面中心；默认每帧步长约 **8°/9°**（比旧版大约 +4°），可在参数里再调。

## 方案 A：YOLOv8-Pose（推荐，开源 Ultralytics）

用 **鼻/双眼** 或人体框上部作为目标，默认 **Matplotlib** 显示，避免 OpenCV+Qt 字体刷屏。

```bash
conda activate lerobot
cd /path/to/welcome
pip install -r camera/requirements.txt -r camera/requirements-yolo.txt
python camera/yolo_track_arm.py
```

- 首次运行会自动下载 `yolov8n-pose.pt`。  
- 需要传统 OpenCV 窗口：`--viz opencv`。  
- 可选浅克隆参考源码：`bash camera/scripts/clone_reference_repos.sh`（见 `camera/third_party/README.md`）。

## 方案 B：OpenCV Haar 人脸

```bash
pip install -r camera/requirements.txt
```

机械臂串口权限、`--robot-id` 与标定文件等约定，与仓库 `arm_driver/README.md` 一致。

## 运行

```bash
# 摄像头 + 机械臂（默认摄像头 /dev/video0，机械臂 /dev/ttyACM0）
python camera/face_track_arm.py

# 指定设备
python camera/face_track_arm.py --camera /dev/video0 --robot-port /dev/ttyACM0 --robot-id my_awesome_follower_arm
```

仅调试摄像头、不连臂：

```bash
python camera/face_track_arm.py --camera-only
```

窗口内 **按 Q** 退出。

## 参数说明（常用）

| 参数 | 含义 |
|------|------|
| `--face-anchor-y` | 追踪点在人脸框内的高度比例（默认约 0.38），对准眼/鼻区域，使「上下」误差更明显 |
| `--pan-gain` / `--lift-gain` | 水平/垂直增益；垂直默认较大，避免只有 1 号关节在动 |
| `--max-pan-step` / `--max-lift-step` | 每帧基准步长（度），再乘对应 gain |
| `--dead-zone-h` / `--dead-zone-v` | 水平与垂直**分开**死区，避免互相拖累 |
| `--invert-pan` / `--invert-lift` | 方向反了时打开 |

摄像头安装方向不同会导致「人往左走臂却往右转」，此时先试 **`--invert-pan`** 或 **`--invert-lift`**。

若终端刷屏 **`QFontDatabase: Cannot find font directory`**：来自 conda 里 OpenCV 的 Qt 界面，**不影响追踪**；可装系统字体减轻：`sudo apt install fonts-dejavu-core`，或忽略。

## 安全提示

追踪环为**比例 + 每帧限幅**，请在无障碍、可急停（拔电）的环境下测试；首次建议减小 `--max-pan-step`。
