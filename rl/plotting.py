"""Turns rl/train.py's training_log.csv into the win-rate-vs-iteration learning
curve -- the single most important portfolio artifact per the project plan."""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def plot_training_curve(log_path: Path, out_path: Path, smooth_window: int = 3) -> None:
    df = pd.read_csv(log_path)
    fig, ax = plt.subplots(figsize=(8, 5))

    ax.plot(df["step"], df["vs_random_win_rate"], "o-", alpha=0.35, color="tab:blue", label="vs random (raw)")
    ax.plot(df["step"], df["vs_heuristic_win_rate"], "o-", alpha=0.35, color="tab:orange", label="vs heuristic (raw)")
    if len(df) >= smooth_window:
        ax.plot(df["step"], df["vs_random_win_rate"].rolling(smooth_window, min_periods=1).mean(),
                color="tab:blue", linewidth=2.5, label=f"vs random ({smooth_window}-pt avg)")
        ax.plot(df["step"], df["vs_heuristic_win_rate"].rolling(smooth_window, min_periods=1).mean(),
                color="tab:orange", linewidth=2.5, label=f"vs heuristic ({smooth_window}-pt avg)")

    ax.axhline(0.5, color="gray", linestyle="--", linewidth=1, label="50% (coin flip)")
    ax.set_xlabel("training timesteps")
    ax.set_ylabel("win rate (30 eval episodes/point)")
    ax.set_title("Self-play PPO win rate vs. baselines")
    ax.set_ylim(0, 1)
    ax.legend(loc="upper left", fontsize=8)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=str, default=str(PROJECT_ROOT / "checkpoints" / "training_log.csv"))
    parser.add_argument("--out", type=str, default=str(PROJECT_ROOT / "checkpoints" / "training_curve.png"))
    args = parser.parse_args()
    plot_training_curve(Path(args.log), Path(args.out))
