#!/usr/bin/env python3
"""Inspect LeRobot dataset and show task breakdown."""

import argparse
from pathlib import Path

import pandas as pd


def inspect_dataset(repo_id: str, root: str | None = None):
    """Inspect dataset and show task/episode breakdown."""

    if root:
        dataset_path = Path(root).expanduser() / repo_id
    else:
        dataset_path = Path(f"~/.cache/huggingface/lerobot/{repo_id}").expanduser()

    if not dataset_path.exists():
        print(f"Dataset not found: {dataset_path}")
        return

    # Read episode metadata
    episodes_dir = dataset_path / "meta/episodes"
    dfs = []
    for chunk_dir in sorted(episodes_dir.iterdir()):
        if chunk_dir.is_dir():
            for f in sorted(chunk_dir.glob("*.parquet")):
                dfs.append(pd.read_parquet(f))

    if not dfs:
        print("No episode metadata found.")
        return

    episodes_df = pd.concat(dfs, ignore_index=True)

    # Extract task string from array
    episodes_df["task"] = episodes_df["tasks"].apply(
        lambda x: x[0] if hasattr(x, "__len__") and len(x) > 0 else "unknown"
    )

    # Summary
    print(f"Dataset: {repo_id}")
    print(f"Path: {dataset_path}")
    print(f"Total episodes: {len(episodes_df)}")
    print(f"Total frames: {episodes_df['length'].sum():,}")
    print()

    # Task breakdown
    print("Episodes by task:")
    print("-" * 60)
    print(f"{'Task':<20} {'Episodes':>10} {'Frames':>12} {'Ep Range':<20}")
    print("-" * 60)

    for task in sorted(episodes_df["task"].unique()):
        group = episodes_df[episodes_df["task"] == task]
        eps = sorted(group["episode_index"].tolist())
        ep_range = f"{eps[0]}-{eps[-1]}" if len(eps) > 1 else str(eps[0])
        print(f"{task:<20} {len(group):>10} {group['length'].sum():>12,} {ep_range:<20}")

    print("-" * 60)
    print(f"{'TOTAL':<20} {len(episodes_df):>10} {episodes_df['length'].sum():>12,}")
    print()

    # Camera info
    video_cols = [c for c in episodes_df.columns if c.startswith("videos/")]
    cameras = set(c.split("/")[1] for c in video_cols)
    if cameras:
        print(f"Cameras: {', '.join(sorted(cameras))}")


def list_episodes(repo_id: str, task: str | None = None, root: str | None = None):
    """List individual episodes, optionally filtered by task."""

    if root:
        dataset_path = Path(root).expanduser() / repo_id
    else:
        dataset_path = Path(f"~/.cache/huggingface/lerobot/{repo_id}").expanduser()

    # Read episode metadata
    episodes_dir = dataset_path / "meta/episodes"
    dfs = []
    for chunk_dir in sorted(episodes_dir.iterdir()):
        if chunk_dir.is_dir():
            for f in sorted(chunk_dir.glob("*.parquet")):
                dfs.append(pd.read_parquet(f))

    episodes_df = pd.concat(dfs, ignore_index=True)
    episodes_df["task"] = episodes_df["tasks"].apply(
        lambda x: x[0] if hasattr(x, "__len__") and len(x) > 0 else "unknown"
    )

    if task:
        episodes_df = episodes_df[episodes_df["task"] == task]

    print(f"{'Ep':>4} {'Task':<20} {'Frames':>8} {'Duration':>10}")
    print("-" * 50)

    for _, row in episodes_df.iterrows():
        duration = row["length"] / 30  # Assuming 30 fps
        print(f"{row['episode_index']:>4} {row['task']:<20} {row['length']:>8} {duration:>9.1f}s")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inspect LeRobot dataset")
    parser.add_argument("--repo-id", "-r", default="local/act_pick_place",
                        help="Dataset repository ID")
    parser.add_argument("--root", help="Custom root directory")
    parser.add_argument("--list", "-l", action="store_true",
                        help="List individual episodes")
    parser.add_argument("--task", "-t", help="Filter by task (with --list)")
    args = parser.parse_args()

    if args.list:
        list_episodes(args.repo_id, args.task, args.root)
    else:
        inspect_dataset(args.repo_id, args.root)
