"""Self-play MaskablePPO training loop. See RULES.md / project plan for why
MaskablePPO (rather than a from-scratch PPO) and why the checkpoint-pool league
(rather than pure self-play) -- the engineering effort here goes into the league
and evaluation harness, not reimplementing PPO's math.
"""

import argparse
from pathlib import Path

from sb3_contrib import MaskablePPO
from stable_baselines3.common.callbacks import BaseCallback

from rl.baselines.heuristic_agent import heuristic_policy
from rl.baselines.random_agent import random_policy
from rl.checkpoint_pool import CheckpointPool
from rl.env import GoStopEnv
from rl.evaluate import run_match
from rl.model_agent import make_model_policy
from rl.self_play_env import GoStopSelfPlayEnv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CHECKPOINT_DIR = PROJECT_ROOT / "checkpoints"


class SelfPlayCheckpointCallback(BaseCallback):
    def __init__(self, checkpoint_pool: CheckpointPool, save_freq: int, eval_freq: int,
                 eval_episodes: int, log_path: Path, verbose: int = 0):
        super().__init__(verbose)
        self.checkpoint_pool = checkpoint_pool
        self.save_freq = save_freq
        self.eval_freq = eval_freq
        self.eval_episodes = eval_episodes
        self.log_path = log_path
        self._last_save = 0
        self._last_eval = 0
        if not self.log_path.exists():
            self.log_path.write_text("step,vs_random_win_rate,vs_heuristic_win_rate\n")

    def _on_training_start(self) -> None:
        # When resuming from a checkpoint, num_timesteps already reflects the
        # prior run's progress -- start the save/eval counters from there instead
        # of 0, or the very first _on_step() would immediately re-save/re-eval.
        self._last_save = self.num_timesteps
        self._last_eval = self.num_timesteps

    def _on_step(self) -> bool:
        if self.num_timesteps - self._last_save >= self.save_freq:
            self._last_save = self.num_timesteps
            self.checkpoint_pool.save(self.model, self.num_timesteps)
        if self.num_timesteps - self._last_eval >= self.eval_freq:
            self._last_eval = self.num_timesteps
            self._evaluate_and_log()
        return True

    def _evaluate_and_log(self) -> None:
        policy = make_model_policy(self.model, deterministic=True)
        vs_random = run_match(policy, random_policy, self.eval_episodes, base_seed=self.num_timesteps)
        vs_heuristic = run_match(policy, heuristic_policy, self.eval_episodes, base_seed=self.num_timesteps + 1)
        with open(self.log_path, "a") as f:
            f.write(f"{self.num_timesteps},{vs_random['win_rate_a']},{vs_heuristic['win_rate_a']}\n")
        if self.verbose:
            print(f"[step {self.num_timesteps}] vs_random={vs_random['win_rate_a']:.2f} "
                  f"vs_heuristic={vs_heuristic['win_rate_a']:.2f}")


def train(total_timesteps: int, checkpoint_dir: Path = DEFAULT_CHECKPOINT_DIR, save_freq: int = 5000,
          eval_freq: int = 5000, eval_episodes: int = 50, n_steps: int = 1024, batch_size: int = 64,
          seed: int = 0, verbose: int = 1, resume_from: Path | None = None, opponent_policy=None):
    """opponent_policy=None (default) trains against the self-play league (see
    CheckpointPool). Passing a fixed policy (e.g. heuristic_policy) instead trains
    against only that opponent the whole run -- used for the league-vs-single-
    opponent ablation; see README's Results section for why that comparison matters."""
    checkpoint_dir = Path(checkpoint_dir)
    checkpoint_pool = CheckpointPool(checkpoint_dir)
    if opponent_policy is None:
        env = GoStopSelfPlayEnv(checkpoint_pool, seed=seed)
    else:
        env = GoStopEnv(opponent_policy=opponent_policy, seed=seed)
    if resume_from is not None:
        model = MaskablePPO.load(str(resume_from), env=env)
    else:
        model = MaskablePPO("MlpPolicy", env, n_steps=n_steps, batch_size=batch_size, verbose=verbose,
                             seed=seed, policy_kwargs=dict(net_arch=[256, 256]))
    callback = SelfPlayCheckpointCallback(checkpoint_pool, save_freq, eval_freq, eval_episodes,
                                           checkpoint_dir / "training_log.csv", verbose=verbose)
    model.learn(total_timesteps=total_timesteps, callback=callback, reset_num_timesteps=resume_from is None)
    final_path = checkpoint_pool.save(model, model.num_timesteps)
    return model, final_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--timesteps", type=int, default=200_000)
    parser.add_argument("--save-freq", type=int, default=5000)
    parser.add_argument("--eval-freq", type=int, default=5000)
    parser.add_argument("--eval-episodes", type=int, default=50)
    parser.add_argument("--n-steps", type=int, default=1024)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--checkpoint-dir", type=str, default=str(DEFAULT_CHECKPOINT_DIR))
    parser.add_argument("--resume-from", type=str, default=None,
                         help="path to a checkpoint .zip to continue training from")
    parser.add_argument("--opponent", choices=["league", "heuristic", "random"], default="league",
                         help="'league' (default) trains via self-play; 'heuristic'/'random' train "
                              "against only that fixed opponent the whole run (ablation mode)")
    args = parser.parse_args()
    opponent_policy = {"league": None, "heuristic": heuristic_policy, "random": random_policy}[args.opponent]
    train(args.timesteps, checkpoint_dir=Path(args.checkpoint_dir), save_freq=args.save_freq,
          eval_freq=args.eval_freq, eval_episodes=args.eval_episodes, n_steps=args.n_steps,
          batch_size=args.batch_size, seed=args.seed,
          resume_from=Path(args.resume_from) if args.resume_from else None,
          opponent_policy=opponent_policy)
