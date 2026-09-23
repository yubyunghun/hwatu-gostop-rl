"""PPO fine-tuning warm-started from the behavior-cloned policy.

The cloning diagnostic (rl/behavior_cloning.py) showed the network can represent the heuristic
and, once cloned, plays at heuristic level -- something PPO from scratch never reached in 650k
steps. So instead of asking PPO to *discover* a heuristic-level policy, start from one and ask it
only to improve on it.

Two things make that work instead of quietly destroying the cloned policy:

1. Value warm-up. Cloning trains only the policy head; the value head is still random, so PPO's
   first updates would compute advantages from noise and push the good policy around. We first
   fit the value head to Monte-Carlo returns collected by the (frozen) cloned policy.
2. A league seeded with the cloned model itself, so the learner starts out facing heuristic-level
   opponents rather than the near-random pool an empty league falls back to.

Learning rate is also much lower than from-scratch training (3e-4), for the same reason.
"""

import argparse
import shutil
import sys
from pathlib import Path

import numpy as np
import torch

from rl.checkpoint_pool import CheckpointPool
from rl.self_play_env import GoStopSelfPlayEnv
from rl.train import SelfPlayCheckpointCallback

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def warm_up_value(model, env, steps: int, epochs: int = 5, lr: float = 1e-3, batch_size: int = 512,
                  log=print) -> dict:
    """Fits only the value network to discounted Monte-Carlo returns from the (frozen) policy."""
    obs_l, ret_l = [], []
    episode_obs, episode_rew = [], []
    obs, _ = env.reset()
    collected = 0
    while collected < steps:
        mask = env.action_masks()
        action, _ = model.predict(obs, action_masks=mask, deterministic=False)
        next_obs, reward, terminated, truncated, _ = env.step(int(action))
        episode_obs.append(obs)
        episode_rew.append(reward)
        collected += 1
        obs = next_obs
        if terminated or truncated:
            g = 0.0
            returns = []
            for r in reversed(episode_rew):
                g = r + model.gamma * g
                returns.append(g)
            obs_l.extend(episode_obs)
            ret_l.extend(reversed(returns))
            episode_obs, episode_rew = [], []
            obs, _ = env.reset()

    x = torch.as_tensor(np.stack(obs_l).astype(np.float32))
    y = torch.as_tensor(np.array(ret_l, dtype=np.float32))
    policy = model.policy
    value_params = list(policy.mlp_extractor.value_net.parameters()) + list(policy.value_net.parameters())
    optimizer = torch.optim.Adam(value_params, lr=lr)
    variance = float(y.var())

    def mse() -> float:
        policy.set_training_mode(False)
        with torch.no_grad():
            return float(((policy.predict_values(x).flatten() - y) ** 2).mean())

    before = mse()
    rng = np.random.default_rng(0)
    for _ in range(epochs):
        policy.set_training_mode(True)
        order = rng.permutation(len(y))
        for start in range(0, len(y), batch_size):
            idx = torch.as_tensor(order[start:start + batch_size])
            loss = ((policy.predict_values(x[idx]).flatten() - y[idx]) ** 2).mean()
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
    after = mse()
    stats = {"samples": len(y), "return_variance": variance, "mse_before": before, "mse_after": after,
             "explained_variance_after": 1.0 - after / variance if variance > 0 else 0.0}
    log(f"value warm-up: {stats}")
    return stats


def finetune(bc_path: Path, total_timesteps: int, checkpoint_dir: Path, lr: float = 3e-5,
             value_warmup_steps: int = 60_000, save_freq: int = 25_000, eval_freq: int = 25_000,
             eval_episodes: int = 100, seed: int = 0, verbose: int = 1):
    from sb3_contrib import MaskablePPO

    checkpoint_dir = Path(checkpoint_dir)
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    pool = CheckpointPool(checkpoint_dir)
    # The cloned policy is league member #0, so the learner's first opponents are heuristic-level.
    shutil.copy(bc_path, checkpoint_dir / "ckpt_00000000.zip")

    env = GoStopSelfPlayEnv(pool, seed=seed)
    model = MaskablePPO.load(str(bc_path), env=env,
                             custom_objects={"learning_rate": lr, "lr_schedule": lambda _: lr})
    warm = warm_up_value(model, env, steps=value_warmup_steps, log=print if verbose else (lambda *_: None))

    callback = SelfPlayCheckpointCallback(pool, save_freq, eval_freq, eval_episodes,
                                          checkpoint_dir / "training_log.csv", verbose=verbose)
    model.learn(total_timesteps=total_timesteps, callback=callback, reset_num_timesteps=True)
    final_path = pool.save(model, model.num_timesteps)
    return model, final_path, warm


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--bc-model", type=str, default="checkpoints_bc/bc_model.zip")
    parser.add_argument("--timesteps", type=int, default=400_000)
    parser.add_argument("--lr", type=float, default=3e-5)
    parser.add_argument("--value-warmup-steps", type=int, default=60_000)
    parser.add_argument("--save-freq", type=int, default=25_000)
    parser.add_argument("--eval-freq", type=int, default=25_000)
    parser.add_argument("--eval-episodes", type=int, default=100)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--checkpoint-dir", type=str, default="checkpoints_finetune")
    a = parser.parse_args()
    finetune(PROJECT_ROOT / a.bc_model, a.timesteps, PROJECT_ROOT / a.checkpoint_dir, lr=a.lr,
             value_warmup_steps=a.value_warmup_steps, save_freq=a.save_freq, eval_freq=a.eval_freq,
             eval_episodes=a.eval_episodes, seed=a.seed)
