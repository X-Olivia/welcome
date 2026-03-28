# ACT Training & Ablation Infrastructure Walkthrough

I have implemented an incremental, flexible training pipeline for simple ACT ablations using LeRobot.

## 1. Core Components

### `train_act.py`
The main training script. It runs a single experiment.
- **Key Features**:
  - Connects to `local/act_pick_place` dataset.
  - Automatically handles chunking via `delta_timestamps`.
  - Integrates with WandB for logging.
  - Saves checkpoints to `checkpoints/<experiment_name>`.

### `run_ablations.py`
Orchestrator for running batch experiments.
- **Key Features**:
  - `run_chunk_size_ablation()`: Sweeps `chunk_size` [50, 100].
  - `run_cvae_comparison()`: Compares CVAE enabled vs disabled.
  - Runs experiments in subprocesses to ensure clean state.
  - Logs outputs to `logs/`.
  - Sets `WANDB_MODE=offline` by default (configurable).

### `ablations/act_experiment_tracker.py`
Provides configuration and tracking utilities.
- Defines `ACTExperimentConfig`.
- Handles metrics logging to WandB.

## 2. Usage Guide

### Manual Training (Single Run)
To run a single training experiment manually:
```bash
python train_act.py --chunk_size=100 --epochs=50 --batch_size=8
```

### Running Ablations
To run the automated ablation studies:
```bash
# Run chunk size ablation
python run_ablations.py --mode chunk

# Run CVAE comparison
python run_ablations.py --mode cvae

# Run all
python run_ablations.py --mode all
```

## 3. Verification Results
I verified the infrastructure by running the chunk size ablation:
- **Chunk Size 50**: Successfully initialized and started training. Verified `n_action_steps` matches `chunk_size`.
- **Logs**: Checked `logs/ablation_chunk_50.log` and confirmed loss values are being calculated and logged.

## 4. Next Steps
- **WandB Sync**: Run `wandb sync wandb/offline-run-*` to upload your results to the cloud.
- **Full Training**: Increase `epochs` in `run_ablations.py` for meaningful results.
- **Evaluation**: Implement the `EvaluationSuite` in `act_experiment_tracker.py` fully with your specific environment `env.step()` logic if you want automated closed-loop evaluation.

## 5. Performance Optimizations (11 it/s)
We optimized the training speed from **2.5 it/s** to **11 it/s** (on RTX 4080) with the following changes:

### Key Upgrades
1.  **Resolution 224x224 (Critical)**:
    *   **Change**: Resized inputs from 480x640 to 224x224 using `torchvision.transforms` + ImageNet normalization.
    *   **Impact**: Reduced visual tokens from ~900 to ~150 per camera (~6x reduction). Since Transformer attention is $O(N^2)$, this yields massive speedups.
2.  **DataLoader Optimization**:
    *   `num_workers=8`: Parallel video decoding on CPU.
    *   `pin_memory=True`: Faster CPU-to-GPU memory transfer.
    *   `prefetch_factor=2`: Keeps the GPU queue full.
3.  **Auto-Resume**:
    *   Script now automatically finds the latest `epoch_N.pt` and resumes training seamlessly.

### Impact Analysis
*   **Speed**: ~4x throughput improvement.
*   **Performance Trade-off**:
    *   **Pros**: 224x224 matches the standard ResNet ImageNet pre-training, often leading to better feature extraction.
    *   **Cons**: Potential loss of fine-grained spatial details for very small objects. For standard pick-and-place tasks, this is rarely an issue.
