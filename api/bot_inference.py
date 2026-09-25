"""Loads the most recent trained checkpoint (falling back to the heuristic if none
exists yet) and wraps it as the same (engine, legal_actions) -> action policy
signature used everywhere else -- api/, rl/env.py, and rl/evaluate.py all drive
policies through this one calling convention."""

import random
from pathlib import Path

from rl.baselines.heuristic_agent import heuristic_policy
from rl.model_agent import make_model_policy
from rl.search import SearchPolicy

# Sampled hidden worlds per decision when the bot searches. About 0.3 s per decision on average,
# under a second at the 95th percentile (measured), which is fine for an interactive game.
SEARCH_DETERMINIZATIONS = 60

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


def load_search_bot_policy(determinizations: int = SEARCH_DETERMINIZATIONS):
    """The strongest bot: determinized search on top of the heuristic (see rl/search.py).

    It only ever looks at what the bot itself can see (its hand, the field, both capture piles); the
    human's hand is re-sampled from the unseen cards, so serving it doesn't leak hidden information
    to the bot. A fresh SearchPolicy per decision keeps concurrent sessions from sharing state."""
    def policy(engine, legal_actions):
        return SearchPolicy(determinizations=determinizations, min_z=1.0,
                            seed=random.getrandbits(32))(engine, legal_actions)
    return policy
