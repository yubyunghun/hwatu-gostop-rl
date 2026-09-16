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


def plot_comparison(log_a: Path, log_b: Path, out_path: Path, label_a: str, label_b: str,
                     title: str, smooth_window: int = 3) -> None:
    """Overlays two training_log.csv files' vs_heuristic win rate -- the general
    form behind every before/after experiment comparison in this project (the
    league-vs-ablation comparison, the reward-shaping comparison, and any future
    one), so a new experiment never needs a new plotting function."""
    a = pd.read_csv(log_a)
    b = pd.read_csv(log_b)
    fig, ax = plt.subplots(figsize=(8, 5))

    for df, color, label in ((a, "tab:green", label_a), (b, "tab:red", label_b)):
        ax.plot(df["step"], df["vs_heuristic_win_rate"], "o", alpha=0.3, color=color)
        ax.plot(df["step"], df["vs_heuristic_win_rate"].rolling(smooth_window, min_periods=1).mean(),
                color=color, linewidth=2.5, label=f"{label} ({smooth_window}-pt avg)")

    ax.axhline(0.5, color="gray", linestyle="--", linewidth=1, label="50% (coin flip)")
    ax.set_xlabel("training timesteps")
    ax.set_ylabel("win rate vs. heuristic (30 eval episodes/point)")
    ax.set_title(title)
    ax.set_ylim(0, 1)
    ax.legend(loc="upper left", fontsize=8)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    print(f"wrote {out_path}")


def plot_ablation_comparison(league_log: Path, ablation_log: Path, out_path: Path,
                              smooth_window: int = 3) -> None:
    """League self-play vs. single-frozen-heuristic-opponent training, vs_heuristic
    win rate only -- this is the comparison the ablation exists to produce."""
    plot_comparison(league_log, ablation_log, out_path, "league (self-play)",
                     "ablation (frozen heuristic only)",
                     "Self-play league vs. single-opponent training", smooth_window)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=str, default=str(PROJECT_ROOT / "checkpoints" / "training_log.csv"))
    parser.add_argument("--out", type=str, default=str(PROJECT_ROOT / "checkpoints" / "training_curve.png"))
    parser.add_argument("--compare-ablation", type=str, default=None,
                         help="path to the ablation run's training_log.csv; if given, also writes "
                              "an ablation-comparison plot instead of the single-run curve")
    parser.add_argument("--compare-out", type=str,
                         default=str(PROJECT_ROOT / "checkpoints" / "ablation_comparison.png"))
    args = parser.parse_args()
    if args.compare_ablation:
        plot_ablation_comparison(Path(args.log), Path(args.compare_ablation), Path(args.compare_out))
    else:
        plot_training_curve(Path(args.log), Path(args.out))
