"""Wraps a loaded MaskablePPO model as an (engine, legal_actions) -> action policy,
the same calling convention as the baseline agents -- so GoStopEnv's opponent_policy
slot doesn't care whether it's driving a random bot, the heuristic, or a checkpoint.
"""

from engine.engine import GoStopEngine
from rl.action_space import legal_action_mask
from rl.obs_encoding import encode


def make_model_policy(model, deterministic: bool = False):
    def policy(engine: GoStopEngine, legal_actions) -> int:
        obs = encode(engine)
        mask = legal_action_mask(engine)
        action, _ = model.predict(obs, action_masks=mask, deterministic=deterministic)
        return int(action)

    return policy
