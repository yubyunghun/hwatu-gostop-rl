"""Loads the most recent trained checkpoint (falling back to the heuristic if none
exists yet) and wraps it as the same (engine, legal_actions) -> action policy
signature used everywhere else -- api/, rl/env.py, and rl/evaluate.py all drive
policies through this one calling convention."""

from pathlib import Path

from rl.baselines.heuristic_agent import heuristic_policy
from rl.model_agent import make_model_policy

# Points at whichever checkpoint directory holds the current best model -- update
# this when a new experiment (see README's Results section) becomes the best one.
DEFAULT_CHECKPOINT_DIR = Path(__file__).resolve().parent.parent / "checkpoints_finetune"


def latest_checkpoint(checkpoint_dir: Path = DEFAULT_CHECKPOINT_DIR) -> Path | None:
    files = sorted(Path(checkpoint_dir).glob("ckpt_*.zip"))
    return files[-1] if files else None


def load_bot_policy(checkpoint_dir: Path = DEFAULT_CHECKPOINT_DIR):
    path = latest_checkpoint(checkpoint_dir)
    if path is None:
        return heuristic_policy
    from sb3_contrib import MaskablePPO
    model = MaskablePPO.load(str(path))
    return make_model_policy(model, deterministic=True)
