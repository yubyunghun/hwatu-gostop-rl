"""GoStopEnv: a single-agent-style Gymnasium wrapper around GoStopEngine for a
2-player hand. The env always presents the "learner" seat's perspective; the other
seat's turns are resolved internally by `opponent_policy` (defaults to random).
This is the shape self_play_env.py (phase 4) builds on, swapping in a policy
sampled from a checkpoint pool instead of a fixed baseline.

Episode = one hand (see RULES.md section 10 -- go/stop is inherently per-hand).
Reward is 0 until termination, then the signed final score differential divided
by SCORE_REWARD_SCALE (nagari -> 0 for both sides).
"""

import random

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from engine.engine import GoStopEngine
from rl.action_space import ACTION_SIZE, apply_action, legal_action_mask
from rl.baselines.random_agent import random_policy
from rl.obs_encoding import OBS_SIZE, encode

SCORE_REWARD_SCALE = 40.0


class GoStopEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, opponent_policy=random_policy, num_players: int = 2, seed: int | None = None):
        super().__init__()
        if num_players != 2:
            raise ValueError("GoStopEnv v1 only supports 2 players (see project plan scope)")
        self.action_space = spaces.Discrete(ACTION_SIZE)
        self.observation_space = spaces.Box(low=0.0, high=np.inf, shape=(OBS_SIZE,), dtype=np.float32)
        self.opponent_policy = opponent_policy
        self.num_players = num_players
        self._rng = np.random.default_rng(seed)
        self.engine: GoStopEngine | None = None
        self.learner_seat: int = 0

    def action_masks(self) -> np.ndarray:
        return legal_action_mask(self.engine)

    def reset(self, *, seed: int | None = None, options=None):
        super().reset(seed=seed)
        if seed is not None:
            self._rng = np.random.default_rng(seed)
        engine_rng = random.Random(int(self._rng.integers(0, 2**31 - 1)))
        self.learner_seat = int(self._rng.integers(0, self.num_players))
        self.engine = GoStopEngine(num_players=self.num_players, dealer=0, rng=engine_rng)
        self._run_opponent_turns()
        return encode(self.engine), {}

    def step(self, action: int):
        if self.engine.state.turn != self.learner_seat:
            raise RuntimeError("step() called when it is not the learner's turn")
        apply_action(self.engine, int(action))
        if not self.engine.state.hand_over:
            self._run_opponent_turns()

        terminated = self.engine.state.hand_over
        reward = self._terminal_reward() if terminated else 0.0
        return encode(self.engine), reward, terminated, False, {}

    def _terminal_reward(self) -> float:
        result = self.engine.state.result
        if result.nagari:
            return 0.0
        return result.scores[self.learner_seat] / SCORE_REWARD_SCALE

    def _run_opponent_turns(self) -> None:
        s = self.engine.state
        while not s.hand_over and s.turn != self.learner_seat:
            mask = legal_action_mask(self.engine)
            legal = np.flatnonzero(mask)
            action = self.opponent_policy(self.engine, legal)
            apply_action(self.engine, int(action))
