
import torch
import numpy as np
import time
import argparse
from pathlib import Path
from torchvision import transforms
from PIL import Image

# LeRobot Imports
from lerobot.robots.so_follower import SO101Follower, SO101FollowerConfig
from lerobot.cameras.opencv import OpenCVCameraConfig
from lerobot.cameras.realsense import RealSenseCameraConfig
from lerobot.policies.act.modeling_act import ACTPolicy
from lerobot.policies.act.configuration_act import ACTConfig
from lerobot.configs.types import PolicyFeature, FeatureType

def get_robot_config():
    """Create robot configuration matching record.py defaults"""
    # Cameras (name comes from dict key, not config parameter)
    cameras = {
        "side": RealSenseCameraConfig(
            serial_number_or_name="213622301205",
            width=640, height=480, fps=30
        ),
        "overhead": OpenCVCameraConfig(
            index_or_path=0,
            width=640, height=480, fps=30
        ),
        "wrist": OpenCVCameraConfig(
            index_or_path=2,
            width=640, height=480, fps=30
        )
    }
    
    return SO101FollowerConfig(
        port="/dev/ttyACM0",
        id="my_follower_arm",
        cameras=cameras,
    )

def get_policy_config():
    """Create policy config matching train_act.py"""
    # Note: Must match training exactly!
    input_features = {
        "observation.images.side": PolicyFeature(type=FeatureType.VISUAL, shape=(3, 224, 224)),
        "observation.images.overhead": PolicyFeature(type=FeatureType.VISUAL, shape=(3, 224, 224)),
        "observation.images.wrist": PolicyFeature(type=FeatureType.VISUAL, shape=(3, 224, 224)),
        "observation.state": PolicyFeature(type=FeatureType.STATE, shape=(6,)),
    }
    
    output_features = {
        "action": PolicyFeature(type=FeatureType.ACTION, shape=(6,)),
    }

    # Default values from train_act.py (assuming default args)
    # You might need to update these if you changed training args!
    return ACTConfig(
        input_features=input_features,
        output_features=output_features,
        chunk_size=100,
        n_action_steps=100,  # Execute full chunk without temporal ensembling
        n_obs_steps=1,
        dim_model=512,
        n_heads=8,
        dim_feedforward=3200,
        n_encoder_layers=4,
        n_decoder_layers=7,
        use_vae=True,
        # No temporal ensembling - execute actions directly
    )

def main(checkpoint_path):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    # 1. Initialize Robot
    print("🤖 Connecting to Robot...")
    robot_cfg = get_robot_config()
    robot = SO101Follower(robot_cfg)
    robot.connect()
    print("✅ Robot Connected")

    # 2. Load Policy
    print(f"🧠 Loading Policy from {checkpoint_path}...")
    policy_cfg = get_policy_config()
    policy = ACTPolicy(policy_cfg)
    
    state_dict = torch.load(checkpoint_path, map_location=device)
    policy.load_state_dict(state_dict)
    policy.to(device)
    policy.eval()
    print("✅ Policy Loaded")

    # 3. Preprocessing (Resize to 224x224)
    image_transform = transforms.Compose([
        transforms.Resize((224, 224), antialias=True),
        transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225]
        )
    ])

    # Reset policy state (clears temporal ensemble buffers)
    policy.reset()

    print("\n🟢 Ready! Press Ctrl+C to stop.")

    # Control Loop Variables
    fps = 30
    dt = 1.0 / fps
    
    # Joint names in order (must match training data)
    joint_names = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]
    camera_names = ["side", "overhead", "wrist"]

    try:
        while True:
            start_time = time.perf_counter()

            # --- 1. Get Observation ---
            # Robot returns: joint positions as "joint_name.pos" floats
            #                images as camera_name with shape (H, W, C) uint8
            obs_dict = robot.get_observation()

            # Prepare batch for model
            batch = {}

            # Process State: combine individual joint positions into (1, 6) tensor
            state = torch.tensor(
                [obs_dict[f"{name}.pos"] for name in joint_names],
                dtype=torch.float32
            ).unsqueeze(0).to(device)
            batch["observation.state"] = state

            # Process Images
            for cam_name in camera_names:
                img = obs_dict[cam_name]  # (H, W, C) uint8 numpy array

                # Convert HWC -> CHW and uint8 -> float [0, 1]
                img = torch.from_numpy(img).permute(2, 0, 1).float() / 255.0

                # Apply resize and normalization
                img = image_transform(img)

                # Add batch dim: (C, H, W) -> (1, C, H, W)
                batch[f"observation.images.{cam_name}"] = img.unsqueeze(0).to(device)

            # --- 2. Inference ---
            # select_action handles temporal aggregation statefully
            action = policy.select_action(batch) # Returns (1, 6) tensor
            
            # --- 3. Execute ---
            action_np = action.squeeze(0).cpu().numpy()

            # Convert action array to dict with joint names
            action_dict = {
                f"{name}.pos": float(action_np[i])
                for i, name in enumerate(joint_names)
            }
            robot.send_action(action_dict)
            
            # --- 4. Timing ---
            compute_time = time.perf_counter() - start_time
            sleep_time = max(0, dt - compute_time)
            if sleep_time > 0:
                time.sleep(sleep_time)
            else:
                print(f"⚠️ Lag: {compute_time*1000:.1f}ms")

    except KeyboardInterrupt:
        print("\n🛑 Stop signal received.")
    finally:
        robot.disconnect()
        print("🔌 Robot Disconnected")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=str, required=True, help="Path to .pt checkpoint")
    args = parser.parse_args()
    
    main(args.checkpoint)
