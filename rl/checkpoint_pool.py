"""Sampling pool of past checkpoints used as self-play opponents. Mixing in a
fixed floor of random/heuristic opponents (rather than pure self-play against
only recent checkpoints) is what prevents the classic self-play failure mode
where two co-evolving policies converge on a narrow pattern that only beats
each other. See RULES.md/project plan for why this floor matters.
"""

import random
from pathlib import Path

from rl.baselines.heuristic_agent import heuristic_policy
from rl.baselines.random_agent import random_policy
from rl.model_agent import make_model_policy

RANDOM_FRAC = 0.1
HEURISTIC_FRAC = 0.1
RECENT_WINDOW = 5


class CheckpointPool:
    def __init__(self, checkpoint_dir, random_frac=RANDOM_FRAC, heuristic_frac=HEURISTIC_FRAC,
                 recent_window=RECENT_WINDOW, rng: random.Random | None = None):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.random_frac = random_frac
        self.heuristic_frac = heuristic_frac
        self.recent_window = recent_window
        self.rng = rng or random.Random()
        self._model_cache: dict[str, object] = {}

    def save(self, model, step: int) -> Path:
        path = self.checkpoint_dir / f"ckpt_{step:08d}.zip"
        model.save(str(path))
        return path

    def recent_checkpoints(self) -> list[Path]:
        files = sorted(self.checkpoint_dir.glob("ckpt_*.zip"))
        return files[-self.recent_window:]

    def sample_policy(self):
        recent = self.recent_checkpoints()
        if not recent:
            # Nothing trained yet: fall back to baselines only.
            return heuristic_policy if self.rng.random() < 0.5 else random_policy

        r = self.rng.random()
        if r < self.random_frac:
            return random_policy
        if r < self.random_frac + self.heuristic_frac:
            return heuristic_policy
        return self._load_policy(self.rng.choice(recent))

    def _load_policy(self, path: Path):
        key = str(path)
        if key not in self._model_cache:
            from sb3_contrib import MaskablePPO
            self._model_cache[key] = make_model_policy(MaskablePPO.load(key))
        return self._model_cache[key]
