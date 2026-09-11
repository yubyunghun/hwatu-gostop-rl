import numpy as np

from engine.engine import GoStopEngine

_default_rng = np.random.default_rng()


def random_policy(engine: GoStopEngine, legal_actions: np.ndarray) -> int:
    return int(_default_rng.choice(legal_actions))
