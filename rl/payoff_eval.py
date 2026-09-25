"""Mean payoff (score differential) against the heuristic -- the quantity PPO is actually trained
to maximize, which win rate does not capture.

Win rate only counts who won. But the reward is the final settlement: winning bigger (go bonuses,
gwang/pi-bak multipliers) pays more, and a policy could earn more per game without winning more
games. So this reports the mean payoff and, because deal luck dominates payoff variance, a *paired*
difference against the heuristic playing the same seat of the same deal.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

from rl.baselines.heuristic_agent import heuristic_policy
from rl.evaluate import HELDOUT_EVAL_SEED, episode_setup, play_episode
from rl.final_eval import checkpoints_for
from rl.model_agent import make_model_policy

PROJECT_ROOT = Path(__file__).resolve().parent.parent

MODELS = {
    "cloned heuristic (BC)": "checkpoints_bc/bc_model.zip",
    "BC + PPO fine-tune": "checkpoints_finetune",
    "PPO from scratch (shaping)": "checkpoints_reward_shaping",
    "PPO from scratch (sparse)": "checkpoints",
}


def payoffs(policy, opponent, games: int, seed: int) -> np.ndarray:
    """Payoff to `policy` per game (nagari = 0), cycling seat and dealer like run_match."""
    out = np.zeros(games)
    for i in range(games):
        swapped, dealer = episode_setup(i)
        first, second = (opponent, policy) if swapped else (policy, opponent)
        result = play_episode(first, second, seed=seed + i, dealer=dealer)
        me = 1 if swapped else 0
        out[i] = 0.0 if result.nagari else result.scores[me]
    return out


def summarize(x: np.ndarray) -> dict:
    se = float(x.std(ddof=1) / np.sqrt(len(x)))
    return {"mean": float(x.mean()), "se": se, "ci_low": float(x.mean() - 1.96 * se),
            "ci_high": float(x.mean() + 1.96 * se), "n": int(len(x))}


def decompose(x: np.ndarray) -> dict:
    """Where the mean comes from: how big are the wins and the losses, and how often each."""
    wins, losses = x[x > 0], x[x < 0]
    return {"n_win": int(len(wins)), "n_loss": int(len(losses)), "n_zero": int((x == 0).sum()),
            "mean_when_winning": float(wins.mean()) if len(wins) else None,
            "mean_when_losing": float(losses.mean()) if len(losses) else None}


def main(games: int, seed: int, only: list[str] | None, out_name: str) -> None:
    from sb3_contrib import MaskablePPO

    reference = payoffs(heuristic_policy, heuristic_policy, games, seed)
    report = {"seed": seed, "games": games,
              "heuristic vs itself": {**summarize(reference), **decompose(reference)}}
    print("heuristic vs itself", report["heuristic vs itself"], flush=True)
    series = {}
    for label, location in MODELS.items():
        if only and label not in only:
            continue
        path = checkpoints_for(PROJECT_ROOT / location, 1)[-1]
        policy = make_model_policy(MaskablePPO.load(str(path)), deterministic=True)
        x = payoffs(policy, heuristic_policy, games, seed)
        series[label] = x
        report[label] = {**summarize(x), **decompose(x),
                         "paired_vs_heuristic": summarize(x - reference)}
        print(label, report[label], flush=True)
    if {"BC + PPO fine-tune", "cloned heuristic (BC)"} <= series.keys():
        report["fine-tune minus clone (paired)"] = summarize(
            series["BC + PPO fine-tune"] - series["cloned heuristic (BC)"])
        print("fine-tune minus clone (paired)", report["fine-tune minus clone (paired)"], flush=True)
    out = PROJECT_ROOT / "checkpoints" / out_name
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"wrote {out.name}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--games", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=HELDOUT_EVAL_SEED)
    parser.add_argument("--only", nargs="*", default=None, help="subset of model labels to score")
    parser.add_argument("--out", type=str, default="payoff_eval.json")
    a = parser.parse_args()
    main(a.games, a.seed, a.only, a.out)
