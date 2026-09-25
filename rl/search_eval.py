"""Does search on top of the heuristic beat the heuristic? Plays SearchPolicy against the
heuristic on held-out deals, in parallel, and compares each game to the heuristic playing that
same deal from that same position (a paired comparison, because deal luck dominates payoff).

Position is balanced via rl.evaluate.episode_setup, like every other evaluation here."""

import argparse
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

from rl.baselines.heuristic_agent import heuristic_policy
from rl.evaluate import episode_setup, play_episode, wilson_interval
from rl.search import SearchPolicy

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _play(args):
    i, seed, determinizations, min_z, nodes = args
    swapped, dealer = episode_setup(i)
    me = 1 if swapped else 0
    policy = SearchPolicy(determinizations, min_z, seed=seed + i, nodes=nodes)
    first, second = (heuristic_policy, policy) if swapped else (policy, heuristic_policy)
    got = play_episode(first, second, seed=seed + i, dealer=dealer)
    ref = play_episode(heuristic_policy, heuristic_policy, seed=seed + i, dealer=dealer)

    def pay(r):
        return 0.0 if r.nagari else float(r.scores[me])

    def outcome(r):
        return 0 if r.nagari else (1 if r.winner == me else -1)

    return (pay(got), pay(ref), outcome(got), outcome(ref),
            policy.decisions, policy.searched, policy.deviations)


def summarize(x: np.ndarray) -> dict:
    se = float(x.std(ddof=1) / np.sqrt(len(x)))
    return {"mean": float(x.mean()), "ci_low": float(x.mean() - 1.96 * se),
            "ci_high": float(x.mean() + 1.96 * se)}


def run(games: int, determinizations: int, min_z: float, seed: int, workers: int,
        nodes: str = "all") -> dict:
    jobs = [(i, seed, determinizations, min_z, nodes) for i in range(games)]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        rows = list(pool.map(_play, jobs, chunksize=4))
    arr = np.array(rows, dtype=float)
    pay_s, pay_h, out_s, out_h = arr[:, 0], arr[:, 1], arr[:, 2], arr[:, 3]
    decisions, searched, deviations = arr[:, 4].sum(), arr[:, 5].sum(), arr[:, 6].sum()

    def wins(o):
        w, l = int((o == 1).sum()), int((o == -1).sum())
        lo, hi = wilson_interval(w, games)
        return {"wins": w, "losses": l, "draws": int((o == 0).sum()),
                "win_rate": w / games, "ci_low": lo, "ci_high": hi}

    return {
        "games": games, "determinizations": determinizations, "min_z": min_z, "seed": seed,
        "nodes": nodes,
        "search_payoff": summarize(pay_s), "heuristic_payoff": summarize(pay_h),
        "paired_payoff_search_minus_heuristic": summarize(pay_s - pay_h),
        "search_outcomes": wins(out_s), "heuristic_outcomes": wins(out_h),
        "decisions": int(decisions), "searched": int(searched), "deviations": int(deviations),
        "deviation_rate_of_searched": float(deviations / searched) if searched else 0.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--games", type=int, default=240)
    parser.add_argument("--determinizations", type=int, default=60)
    parser.add_argument("--min-z", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=4_000_000)
    parser.add_argument("--workers", type=int, default=10)
    parser.add_argument("--nodes", choices=["all", "play", "gostop"], default="all")
    parser.add_argument("--out", type=str, default=None)
    a = parser.parse_args()
    report = run(a.games, a.determinizations, a.min_z, a.seed, a.workers, a.nodes)
    text = json.dumps(report, indent=2)
    print(text)
    if a.out:
        (PROJECT_ROOT / "checkpoints" / a.out).write_text(text, encoding="utf-8")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
