
import torch
import sys
import numpy as np
from torch.utils.data import DataLoader
from lerobot.datasets.lerobot_dataset import LeRobotDataset
from lerobot.policies.act.modeling_act import ACTPolicy
from lerobot.policies.act.configuration_act import ACTConfig
from lerobot.configs.types import PolicyFeature, FeatureType
from pathlib import Path
import tqdm

# Import experiment tracker
from ablations.act_experiment_tracker import ACTExperimentConfig, ACTMetricsTracker


def train(exp_config: ACTExperimentConfig = None):
    # 1. Experiment Configuration
    if exp_config is None:
        # Default config for direct run
        exp_config = ACTExperimentConfig(
            experiment_name="act_manual_run",
            chunk_size=100,
            batch_size=8,
            kl_weight=10.0,
            use_cvae=True,
            num_epochs=5,
            notes="Manual run",
            dataset_name="local/act_pick_place"
        )
    
    # Initialize tracker
    tracker = ACTMetricsTracker(exp_config)
    print(f"🚀 Training Experiment: {exp_config.experiment_name}")
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    # 2. Dataset
    print(f"� Loading dataset: {exp_config.dataset_name}")
    
    # Configure delta timestamps for ACT chunking
    fps = 30
    delta_timestamps = {
        "action": [i / fps for i in range(exp_config.chunk_size)],
        "observation.images.side": [0.0],
        "observation.images.overhead": [0.0],
        "observation.images.wrist": [0.0],
        "observation.state": [0.0],
    }
    
    dataset = LeRobotDataset(repo_id=exp_config.dataset_name, delta_timestamps=delta_timestamps)
    
    # 2.1 Add Transforms (Critical for speed)
    from torchvision import transforms
    # Resize to standard ResNet input size (224x224) to reduce token count
    # 480x640 -> 300 tokens/cam -> O(N^2) explosion
    # 224x224 -> 49 tokens/cam -> Fast
    dataset.image_transforms = transforms.Compose([
        transforms.Resize((224, 224), antialias=True),
        transforms.Normalize(
            mean=[0.485, 0.456, 0.406], # ImageNet defaults
            std=[0.229, 0.224, 0.225]
        )
    ])
    
    dataloader = DataLoader(
        dataset, 
        batch_size=exp_config.batch_size, 
        shuffle=True, 
        num_workers=8, # Increased for better IO
        pin_memory=True, # Faster transfer to GPU
        prefetch_factor=2, # Buffer batches
        drop_last=True,
        persistent_workers=True # Keep workers alive
    )

    # 3. Policy Config Mapping
    # Note: We must match the transformed image size here
    input_features = {
        "observation.images.side": PolicyFeature(type=FeatureType.VISUAL, shape=(3, 224, 224)),
        "observation.images.overhead": PolicyFeature(type=FeatureType.VISUAL, shape=(3, 224, 224)),
        "observation.images.wrist": PolicyFeature(type=FeatureType.VISUAL, shape=(3, 224, 224)),
        "observation.state": PolicyFeature(type=FeatureType.STATE, shape=(6,)),
    }
    
    output_features = {
        "action": PolicyFeature(type=FeatureType.ACTION, shape=(6,)),
    }

    act_config = ACTConfig(
        input_features=input_features,
        output_features=output_features,
        chunk_size=exp_config.chunk_size,
        n_action_steps=exp_config.chunk_size,
        n_obs_steps=1,
        dim_model=exp_config.hidden_dim,
        n_heads=8,
        dim_feedforward=exp_config.dim_feedforward,
        n_encoder_layers=exp_config.num_encoder_layers,
        n_decoder_layers=exp_config.num_decoder_layers, 
        use_vae=exp_config.use_cvae,
        kl_weight=exp_config.kl_weight,
    )

    # Initialize Policy

    # Initialize Policy
    print("🤖 Initializing ACT Policy...")
    policy = ACTPolicy(act_config)
    policy.to(device)
    
    # Auto-Resume Logic
    checkpoint_dir = Path(f"checkpoints/{exp_config.experiment_name}")
    start_epoch = 0
    
    if checkpoint_dir.exists():
        checkpoints = sorted([p for p in checkpoint_dir.glob("epoch_*.pt")], 
                           key=lambda x: int(x.stem.split('_')[1]))
        if checkpoints:
            latest_ckpt = checkpoints[-1]
            tqdm.tqdm.write(f"🔄 Resuming from checkpoint: {latest_ckpt}")
            
            # Load weights
            state_dict = torch.load(latest_ckpt, map_location=device)
            policy.load_state_dict(state_dict)
            
            # Set start epoch to next epoch
            start_epoch = int(latest_ckpt.stem.split('_')[1]) + 1
            print(f"▶️  Continuing from Epoch {start_epoch}")
        else:
            print("🆕 No checkpoints found. Starting fresh.")
    else:
        print("🆕 Experiment dir not found. Starting fresh.")

    policy.train()

    optimizer = torch.optim.AdamW(
        policy.parameters(), 
        lr=exp_config.learning_rate, 
        weight_decay=1e-4
    )

    # 4. Training Loop
    print(f"🏃 Starting training for {exp_config.num_epochs} epochs (from {start_epoch})...")
    
    step = start_epoch * len(dataloader) # Approximate step count
    for epoch in range(start_epoch, exp_config.num_epochs):
        epoch_loss = []
        epoch_l1 = []
        epoch_kl = []
        
        with tqdm.tqdm(dataloader, desc=f"Epoch {epoch}") as pbar:
            for batch in pbar:
                # Move batch to device
                for k, v in batch.items():
                    if isinstance(v, torch.Tensor):
                        batch[k] = v.to(device)
                
                # Fix dimensions for ACTPolicy (expects B, D for state, not B, 1, D)
                if "observation.state" in batch:
                    batch["observation.state"] = batch["observation.state"].squeeze(1)
                
                # Forward
                loss, loss_dict = policy(batch)
                
                # Backward
                optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(policy.parameters(), 1.0)
                optimizer.step()
                
                # Tracking
                l1_loss = loss_dict['l1_loss']
                kl_loss = loss_dict.get('kld_loss', 0.0)
                
                epoch_loss.append(loss.item())
                epoch_l1.append(l1_loss)
                epoch_kl.append(kl_loss)
                
                pbar.set_postfix({'loss': loss.item(), 'l1': l1_loss})
                
                # Log step
                if step % 10 == 0:
                    tracker.log_training_step(step, {
                        'loss': loss.item(),
                        'l1_loss': l1_loss,
                        'kl_loss': kl_loss
                    })
                step += 1
        
        # Log Epoch
        mean_loss = np.mean(epoch_loss)
        tracker.log_epoch(epoch, step, {
            'total_loss': mean_loss,
            'l1_loss': np.mean(epoch_l1),
            'kl_loss': np.mean(epoch_kl)
        })
        
        # Save checkpoint via tracker
        checkpoint_path = f"checkpoints/{exp_config.experiment_name}/epoch_{epoch}.pt"
        Path(checkpoint_path).parent.mkdir(parents=True, exist_ok=True)
        torch.save(policy.state_dict(), checkpoint_path)
        
        tracker.save_checkpoint_info(epoch, checkpoint_path, {'loss': mean_loss})
        print(f"💾 Saved checkpoint for epoch {epoch}")

    print("✅ Training Complete")
    tracker.finish()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--chunk_size", type=int, default=100)
    parser.add_argument("--batch_size", type=int, default=8)
    parser.add_argument("--kl_weight", type=float, default=10.0)
    parser.add_argument("--no_cvae", action="store_true")
    
    args = parser.parse_args()
    
    config = ACTExperimentConfig(
        experiment_name=f"act_cli_chunk{args.chunk_size}",
        chunk_size=args.chunk_size,
        batch_size=args.batch_size,
        kl_weight=args.kl_weight,
        use_cvae=not args.no_cvae,
        num_epochs=args.epochs,
        dataset_name="local/act_pick_place"
    )
    
    train(config)
