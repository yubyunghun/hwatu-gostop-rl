"""Distilling determinized search (rl/search.py) into the network by supervised learning -- the
same diagnostic/warm-start idea as rl/behavior_cloning.py (which imitates the heuristic), now with
search as the teacher. Search is the first thing in this project that's actually beaten the
heuristic at card play, not just at the go/stop payoff (see README's Results), so the question
here is how much of that edge a fast feedforward network can actually absorb, the same way cloning
the heuristic asked whether the network could represent heuristic-level play at all.

Search is far more expensive per label than the heuristic: every label plays many rollouts
(rl/search.py:SearchPolicy.value_table), not one rule evaluation. Two things make a dataset of
useful size actually feasible to generate:
- Dataset generation runs in parallel worker processes, one game per task (same pattern as
  rl/search_eval.py's ProcessPoolExecutor).
- The default determinizations per label (`--determinizations`) is lower than search's own
  evaluation default (25 here vs. 60 in rl/search_eval.py), trading some teacher quality for a
  dataset size that doesn't take hours to generate. This is a deliberate, documented tradeoff --
  the teacher used to measure search's own strength and the teacher used here are not identical.

Training and evaluation reuse rl/behavior_cloning.py's train_bc/_accuracy unchanged -- only the
teacher and the (parallel) dataset generator differ, so the comparison is clean: same network
architecture, same training loop, same optimizer, as the heuristic clone.
"""

import argparse
import json
import random
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

from engine.engine import GoStopEngine
from rl.action_space import apply_action, legal_action_mask
from rl.baselines.heuristic_agent import heuristic_policy
from rl.baselines.random_agent import random_policy
from rl.behavior_cloning import _accuracy, train_bc
from rl.evaluate import HELDOUT_EVAL_SEED, run_match, wilson_interval
from rl.model_agent import make_model_policy
from rl.obs_encoding import encode
from rl.search import SearchPolicy

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MAX_STEPS_PER_GAME = 500


def _play_one_game(args: tuple) -> tuple:
    game_idx, seed, eps, determinizations, min_z, nodes = args
    noise_rng = np.random.default_rng((seed, game_idx, 1))
    engine = GoStopEngine(num_players=2, dealer=game_idx % 2,
                           rng=random.Random(seed * 1_000_003 + game_idx))
    policy = SearchPolicy(determinizations=determinizations, min_z=min_z,
                           seed=seed * 7_919 + game_idx, nodes=nodes)
    obs_l, act_l, mask_l, dec_l = [], [], [], []
    steps = 0
    while not engine.state.hand_over:
        steps += 1
        if steps > MAX_STEPS_PER_GAME:
            raise RuntimeError("game did not terminate while generating data")
        mask = legal_action_mask(engine)
        legal = np.flatnonzero(mask)
        label = int(policy(engine, legal))
        if not mask[label]:
            raise RuntimeError(f"search chose illegal action {label}")
        obs_l.append(encode(engine))
        act_l.append(label)
        mask_l.append(mask)
        dec_l.append(engine.state.pending_decision.value)
        action = int(noise_rng.choice(legal)) if noise_rng.random() < eps else label
        apply_action(engine, action)
    return obs_l, act_l, mask_l, dec_l


def generate_dataset(num_games: int, eps: float, seed: int, determinizations: int, min_z: float,
                      nodes: str, workers: int) -> dict:
    jobs = [(g, seed, eps, determinizations, min_z, nodes) for g in range(num_games)]
    obs_all, act_all, mask_all, dec_all = [], [], [], []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for obs_l, act_l, mask_l, dec_l in pool.map(_play_one_game, jobs, chunksize=1):
            obs_all.extend(obs_l)
            act_all.extend(act_l)
            mask_all.extend(mask_l)
            dec_all.extend(dec_l)
    return {
        "obs": np.stack(obs_all).astype(np.float32),
        "actions": np.array(act_all, dtype=np.int64),
        "masks": np.stack(mask_all),
        "decisions": np.array(dec_all, dtype=np.int8),
    }


def main(args) -> None:
    out_dir = PROJECT_ROOT / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    train = generate_dataset(args.games, args.eps, args.seed, args.determinizations, args.min_z,
                              args.nodes, args.workers)
    val = generate_dataset(args.val_games, args.eps, args.seed + 1, args.determinizations,
                            args.min_z, args.nodes, args.workers)
    print(f"data: {len(train['actions'])} train / {len(val['actions'])} val states "
          f"in {time.time() - t0:.0f}s", flush=True)

    chance = float(np.mean(1.0 / val["masks"].sum(axis=1)))
    model, history = train_bc(train, val, args.epochs, args.batch_size, args.lr, args.seed)
    acc = _accuracy(model.policy, val)
    model.save(str(out_dir / "distill_model.zip"))

    policy = make_model_policy(model, deterministic=True)
    games = {}
    for name, opp in (("random", random_policy), ("heuristic", heuristic_policy)):
        s = run_match(policy, opp, args.eval_episodes, base_seed=HELDOUT_EVAL_SEED)
        low, high = wilson_interval(s["wins_a"], args.eval_episodes)
        games[name] = {**s, "ci_low": low, "ci_high": high}
        print(f"vs {name}: {s['win_rate_a']:.3f}  [{low:.3f}, {high:.3f}]", flush=True)

    report = {
        "teacher": "search", "teacher_determinizations": args.determinizations,
        "teacher_min_z": args.min_z, "teacher_nodes": args.nodes,
        "train_states": int(len(train["actions"])), "val_states": int(len(val["actions"])),
        "eps": args.eps, "epochs": args.epochs, "lr": args.lr, "batch_size": args.batch_size,
        "random_guess_agreement": chance, "val_agreement": acc, "history": history,
        "games": games,
    }
    (out_dir / "distill_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("random_guess_agreement", "val_agreement")}, indent=2))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--games", type=int, default=1500)
    parser.add_argument("--val-games", type=int, default=200)
    parser.add_argument("--eps", type=float, default=0.2,
                        help="probability of executing a random legal move (labels stay search's)")
    parser.add_argument("--determinizations", type=int, default=25,
                        help="sampled worlds per label -- lower than search_eval's default (60) to "
                             "keep dataset generation tractable; a deliberate quality/speed tradeoff")
    parser.add_argument("--min-z", type=float, default=1.0)
    parser.add_argument("--nodes", choices=["all", "play", "gostop"], default="all")
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=512)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--eval-episodes", type=int, default=300)
    parser.add_argument("--workers", type=int, default=10)
    parser.add_argument("--out-dir", type=str, default="checkpoints_distill")
    main(parser.parse_args())
