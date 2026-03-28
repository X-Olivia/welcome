# SO-101 Robot Arm Commands Cheatsheet

## Setup

```bash
# Activate virtual environment
source .venv/bin/activate

# Grant port access (run after each reboot or add user to dialout group)
sudo chmod 666 /dev/ttyACM0 /dev/ttyACM1

# Permanent fix - add user to dialout group (requires logout/login)
sudo usermod -aG dialout $USER
```

## Port Configuration

| Device       | Port         |
|--------------|--------------|
| Follower arm | /dev/ttyACM0 |
| Leader arm   | /dev/ttyACM1 |
| Robot camera | /dev/video2  |

## LeRobot Commands

### Find USB Ports
```bash
lerobot-find-port
```

### Calibrate Follower Arm
```bash
lerobot-calibrate \
    --robot.type=so101_follower \
    --robot.port=/dev/ttyACM0 \
    --robot.id=my_follower_arm
```

### Calibrate Leader Arm
```bash
lerobot-calibrate \
    --teleop.type=so101_leader \
    --teleop.port=/dev/ttyACM1 \
    --teleop.id=my_leader_arm
```

### Teleoperate (Control Follower with Leader)
```bash
lerobot-teleoperate \
    --robot.type=so101_follower \
    --robot.port=/dev/ttyACM0 \
    --robot.id=my_follower_arm \
    --teleop.type=so101_leader \
    --teleop.port=/dev/ttyACM1 \
    --teleop.id=my_leader_arm
```

## Camera

### View Camera Feed
```bash
python view_camera.py --device 2
```

## Calibration Files

Calibration data is stored at:
- Follower: `~/.cache/huggingface/lerobot/calibration/robots/so101_follower/my_follower_arm.json`
- Leader: `~/.cache/huggingface/lerobot/calibration/teleoperators/so101_leader/my_leader_arm.json`

## Troubleshooting

### No serial ports detected
1. Check USB cables are connected
2. Ensure arms are powered on
3. Run `lsusb` to verify devices are detected
4. Check `dmesg | tail -20` for connection errors

### Camera not working
- Use `ls /dev/video*` to list available cameras
- Robot camera is typically `/dev/video2`, webcam is `/dev/video0`

### OpenCV GUI error
If you get "The function is not implemented" error:
```bash
pip uninstall opencv-python-headless
pip install opencv-python
```
