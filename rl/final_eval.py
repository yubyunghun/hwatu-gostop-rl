"""Re-scores each experiment's final checkpoint on a large fresh set of deals, with
95% Wilson confidence intervals.

The per-checkpoint numbers logged during training use only 30 games each, i.e.
roughly +/-8 points of noise -- fine for watching a run, but too coarse to support
claims like "31.7% vs 25.6%". This script exists to put honest error bars on the
comparisons the README makes. Seeds start well above anything training-time
evaluation used, so no deal here was ever seen during a run's own logging.
"""

import argparse
import csv
import sys
from pathlib import Path

import matplotlib.pyplot as plt

from rl.baselines.heuristic_agent import heuristic_policy
from rl.baselines.random_agent import random_policy
from rl.evaluate import run_match, wilson_interval
from rl.model_agent import make_model_policy

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EVAL_BASE_SEED = 1_000_000

# label -> checkpoint directory (the newest ckpt_*.zip in it is the final model)
EXPERIMENTS = {
    "original (sparse reward)": "checkpoints",
    "ablation (heuristic only)": "checkpoints_ablation_heuristic",
    "reward shaping": "checkpoints_reward_shaping",
    "shaping + entropy 0.01": "checkpoints_entropy_tuning",
}


def latest_checkpoint(directory: Path) -> Path:
    files = sorted(directory.glob("ckpt_*.zip"))
    if not files:
        raise FileNotFoundError(f"no checkpoints in {directory}")
    return files[-1]


def score(policy, opponent, episodes: int, seed: int) -> dict:
    stats = run_match(policy, opponent, episodes, base_seed=seed)
    low, high = wilson_interval(stats["wins_a"], episodes)
    return {**stats, "ci_low": low, "ci_high": high}


def pooled_score(paths: list[Path], opponent, episodes_per_ckpt: int, seed: int) -> dict:
    """Pools games from several late checkpoints of one run. This tests the claim
    the README actually makes -- that a run's *late-training* play is better -- rather
    than betting everything on whichever single snapshot the run happened to end on."""
    from sb3_contrib import MaskablePPO

    wins = losses = nagari = games = 0
    for j, path in enumerate(paths):
        policy = make_model_policy(MaskablePPO.load(str(path)), deterministic=True)
        s = run_match(policy, opponent, episodes_per_ckpt, base_seed=seed + 10_000 * j)
        wins += s["wins_a"]
        losses += s["wins_b"]
        nagari += s["nagari"]
        games += episodes_per_ckpt
    low, high = wilson_interval(wins, games)
    return {"episodes": games, "wins_a": wins, "wins_b": losses, "nagari": nagari,
            "win_rate_a": wins / games, "ci_low": low, "ci_high": high}


def main(episodes: int, pooled_k: int, pooled_episodes: int) -> None:
    from sb3_contrib import MaskablePPO

    rows = []
    # Reference rows: the heuristic itself, so the table has a fixed yardstick.
    for label, policy in (("heuristic (reference)", heuristic_policy),):
        for opp_name, opp in (("random", random_policy), ("heuristic", heuristic_policy)):
            rows.append({"model": label, "opponent": opp_name,
                         **score(policy, opp, episodes, EVAL_BASE_SEED)})
            print(rows[-1], flush=True)

    for label, directory in EXPERIMENTS.items():
        path = latest_checkpoint(PROJECT_ROOT / directory)
        policy = make_model_policy(MaskablePPO.load(str(path)), deterministic=True)
        for opp_name, opp in (("random", random_policy), ("heuristic", heuristic_policy)):
            rows.append({"model": label, "opponent": opp_name,
                         **score(policy, opp, episodes, EVAL_BASE_SEED)})
            print(rows[-1], f"({path.name})", flush=True)

    pooled_label = f"heuristic (pooled last {pooled_k} ckpts)"
    for label, directory in EXPERIMENTS.items():
        paths = sorted((PROJECT_ROOT / directory).glob("ckpt_*.zip"))[-pooled_k:]
        rows.append({"model": label, "opponent": pooled_label,
                     **pooled_score(paths, heuristic_policy, pooled_episodes, EVAL_BASE_SEED)})
        print(rows[-1], flush=True)

    out_csv = PROJECT_ROOT / "checkpoints" / "final_eval.csv"
    fields = ["model", "opponent", "episodes", "wins_a", "wins_b", "nagari",
              "win_rate_a", "ci_low", "ci_high"]
    with open(out_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {out_csv.name}")
    plot(rows, PROJECT_ROOT / "checkpoints" / "final_eval.png", episodes, pooled_label)


def plot(rows: list[dict], out_path: Path, episodes: int, pooled_label: str) -> None:
    opponents = ("random", "heuristic", pooled_label)
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.8), sharey=True)
    for ax, opp in zip(axes, opponents):
        subset = [r for r in rows if r["opponent"] == opp]
        labels = [r["model"] for r in subset]
        rates = [r["win_rate_a"] for r in subset]
        err = [[r["win_rate_a"] - r["ci_low"] for r in subset],
               [r["ci_high"] - r["win_rate_a"] for r in subset]]
        ax.bar(range(len(subset)), rates, yerr=err, capsize=4, color="tab:blue", alpha=0.8)
        ax.axhline(0.5, color="gray", linestyle="--", linewidth=1)
        ax.set_xticks(range(len(subset)))
        ax.set_xticklabels(labels, rotation=25, ha="right", fontsize=8)
        ax.set_title(f"final checkpoint vs. {opp}" if opp in ("random", "heuristic")
                     else f"vs. {opp}", fontsize=10)
        ax.set_ylim(0, 1)
    axes[0].set_ylabel("win rate (95% Wilson CI)")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    print(f"wrote {out_path.name}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # the project path contains Korean characters
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes", type=int, default=300)
    parser.add_argument("--pooled-k", type=int, default=5)
    parser.add_argument("--pooled-episodes", type=int, default=200)
    args = parser.parse_args()
    main(args.episodes, args.pooled_k, args.pooled_episodes)
