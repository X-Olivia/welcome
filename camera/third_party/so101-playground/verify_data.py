import torch
from lerobot.datasets.lerobot_dataset import LeRobotDataset

def verify_dataset():
    repo_id = "local/act_pick_place"
    print(f"🔄 Attempting to load dataset: {repo_id}")
    
    try:
        dataset = LeRobotDataset(repo_id=repo_id)
        print(f"✅ Successfully loaded dataset!")
        print(f"   - Episodes: {dataset.num_episodes}")
        print(f"   - Frames: {len(dataset)}")
        print(f"   - Features: {dataset.features}")
        for k, v in dataset.features.items():
            print(f"     {k}: {v} (type: {type(v)})")
        print(f"   - FPS: {dataset.fps}")
        
        # Test accessing an item
        item = dataset[0]
        print(f"\n🔍 First frame check:")
        for key, value in item.items():
            if isinstance(value, torch.Tensor):
                print(f"   - {key}: {type(value)} shape={value.shape}")
            else:
                print(f"   - {key}: {type(value)}")
                
    except Exception as e:
        print(f"❌ Failed to load dataset: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_dataset()
