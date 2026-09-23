"""Behavior cloning of the heuristic baseline -- a diagnostic, and a warm start.

Four different PPO knobs (opponent pool, reward shaping, entropy, more timesteps) all plateau at
~23-27% against the heuristic, which points at something structural instead of any one knob.
The suspect is the observation/architecture: the network sees flattened 48-slot multi-hot
vectors, so "this hand card shares a month with that field card" has to be *learned* as a relation
between slot indices, while the heuristic reads it straight off the rules.

The direct test: train the exact same network (MaskablePPO's policy) by supervised learning to
imitate the heuristic. If it can't reproduce a deterministic rule from this observation, the
representation is the bottleneck and RL was never the problem. If it can, the representation is
fine and the saved model doubles as a warm start for PPO fine-tuning.

Data: play games in which every visited state is labeled with the heuristic's action, but the
action actually *executed* is a random legal move with probability `eps`. That keeps the visited
states from being only the ones the heuristic itself reaches (the DAgger idea), so the network is
trained on states it will meet when its own imperfect play drifts off the heuristic's path.
"""

import argparse
import json
import random
import sys
import time
from pathlib import Path

import numpy as np
import torch

from engine.engine import GoStopEngine
from rl.action_space import apply_action, legal_action_mask
from rl.baselines.heuristic_agent import heuristic_policy
from rl.baselines.random_agent import random_policy
from rl.env import GoStopEnv
from rl.evaluate import HELDOUT_EVAL_SEED, run_match, wilson_interval
from rl.model_agent import make_model_policy
from rl.obs_encoding import encode

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DECISION_NAMES = {1: "PLAY_CARD", 2: "BOMB_DECISION", 3: "GO_STOP"}
MAX_STEPS_PER_GAME = 500


def generate_dataset(num_games: int, eps: float, seed: int) -> dict:
    rng = np.random.default_rng(seed)
    obs_l, act_l, mask_l, dec_l = [], [], [], []
    for g in range(num_games):
        engine = GoStopEngine(num_players=2, dealer=g % 2, rng=random.Random(seed * 1_000_003 + g))
        steps = 0
        while not engine.state.hand_over:
            steps += 1
            if steps > MAX_STEPS_PER_GAME:
                raise RuntimeError("game did not terminate while generating data")
            mask = legal_action_mask(engine)
            legal = np.flatnonzero(mask)
            label = int(heuristic_policy(engine, legal))
            if not mask[label]:
                raise RuntimeError(f"heuristic chose illegal action {label}")
            obs_l.append(encode(engine))
            act_l.append(label)
            mask_l.append(mask)
            dec_l.append(engine.state.pending_decision.value)
            action = int(rng.choice(legal)) if rng.random() < eps else label
            apply_action(engine, action)
    return {
        "obs": np.stack(obs_l).astype(np.float32),
        "actions": np.array(act_l, dtype=np.int64),
        "masks": np.stack(mask_l),
        "decisions": np.array(dec_l, dtype=np.int8),
    }


def _accuracy(policy, data: dict, batch_size: int = 4096) -> dict:
    """Top-1 agreement with the heuristic under the legality mask, overall and per decision type."""
    policy.set_training_mode(False)
    correct = np.zeros(len(data["actions"]), dtype=bool)
    with torch.no_grad():
        for start in range(0, len(correct), batch_size):
            sl = slice(start, start + batch_size)
            obs = torch.as_tensor(data["obs"][sl])
            masks = data["masks"][sl]
            dist = policy.get_distribution(obs, action_masks=masks)
            pred = dist.get_actions(deterministic=True).cpu().numpy()
            correct[sl] = pred == data["actions"][sl]
    out = {"overall": float(correct.mean())}
    for value, name in DECISION_NAMES.items():
        sel = data["decisions"] == value
        if sel.any():
            out[name] = float(correct[sel].mean())
            out[f"{name}_n"] = int(sel.sum())
    return out


def train_bc(train: dict, val: dict, epochs: int, batch_size: int, lr: float, seed: int,
             log=print):
    from sb3_contrib import MaskablePPO

    torch.manual_seed(seed)
    model = MaskablePPO("MlpPolicy", GoStopEnv(seed=seed), seed=seed, verbose=0,
                         policy_kwargs=dict(net_arch=[256, 256]))
    policy = model.policy
    optimizer = torch.optim.Adam(policy.parameters(), lr=lr)
    n = len(train["actions"])
    order_rng = np.random.default_rng(seed)
    history = []
    for epoch in range(1, epochs + 1):
        policy.set_training_mode(True)
        order = order_rng.permutation(n)
        total_loss = 0.0
        for start in range(0, n, batch_size):
            idx = order[start:start + batch_size]
            obs = torch.as_tensor(train["obs"][idx])
            actions = torch.as_tensor(train["actions"][idx])
            _, log_prob, _ = policy.evaluate_actions(obs, actions, action_masks=train["masks"][idx])
            loss = -log_prob.mean()
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * len(idx)
        val_acc = _accuracy(policy, val)
        history.append({"epoch": epoch, "train_loss": total_loss / n, "val_acc": val_acc["overall"]})
        log(f"epoch {epoch:3d}  loss {total_loss / n:.4f}  val agreement {val_acc['overall']:.4f}")
    return model, history


def main(args) -> None:
    out_dir = PROJECT_ROOT / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    train = generate_dataset(args.games, args.eps, seed=args.seed)
    val = generate_dataset(args.val_games, args.eps, seed=args.seed + 1)
    print(f"data: {len(train['actions'])} train / {len(val['actions'])} val states "
          f"in {time.time() - t0:.0f}s", flush=True)

    chance = float(np.mean(1.0 / val["masks"].sum(axis=1)))
    model, history = train_bc(train, val, args.epochs, args.batch_size, args.lr, args.seed)
    acc = _accuracy(model.policy, val)
    model.save(str(out_dir / "bc_model.zip"))

    policy = make_model_policy(model, deterministic=True)
    games = {}
    for name, opp in (("random", random_policy), ("heuristic", heuristic_policy)):
        s = run_match(policy, opp, args.eval_episodes, base_seed=HELDOUT_EVAL_SEED)
        low, high = wilson_interval(s["wins_a"], args.eval_episodes)
        games[name] = {**s, "ci_low": low, "ci_high": high}
        print(f"vs {name}: {s['win_rate_a']:.3f}  [{low:.3f}, {high:.3f}]", flush=True)

    report = {
        "train_states": int(len(train["actions"])), "val_states": int(len(val["actions"])),
        "eps": args.eps, "epochs": args.epochs, "lr": args.lr, "batch_size": args.batch_size,
        "random_guess_agreement": chance, "val_agreement": acc, "history": history,
        "games": games,
    }
    (out_dir / "bc_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("random_guess_agreement", "val_agreement")}, indent=2))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--games", type=int, default=4000)
    parser.add_argument("--val-games", type=int, default=500)
    parser.add_argument("--eps", type=float, default=0.2,
                        help="probability of executing a random legal move (labels stay heuristic)")
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=512)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--eval-episodes", type=int, default=300)
    parser.add_argument("--out-dir", type=str, default="checkpoints_bc")
    main(parser.parse_args())
