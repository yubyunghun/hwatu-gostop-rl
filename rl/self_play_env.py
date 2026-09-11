from rl.checkpoint_pool import CheckpointPool
from rl.env import GoStopEnv


class GoStopSelfPlayEnv(GoStopEnv):
    """GoStopEnv whose opponent is resampled from a CheckpointPool at every reset(),
    instead of a single fixed policy -- this is what phase 4 training actually uses."""

    def __init__(self, checkpoint_pool: CheckpointPool, num_players: int = 2, seed: int | None = None):
        super().__init__(opponent_policy=checkpoint_pool.sample_policy(), num_players=num_players, seed=seed)
        self.checkpoint_pool = checkpoint_pool

    def reset(self, *, seed: int | None = None, options=None):
        self.opponent_policy = self.checkpoint_pool.sample_policy()
        return super().reset(seed=seed, options=options)
