"""Head-to-head evaluation between two (engine, legal_actions) -> action policies.
Used now as the phase-gate check (heuristic must clearly beat random before any
training compute is spent) and later to evaluate trained checkpoints against the
baselines and against each other.
"""

import math
import random

import numpy as np

from engine.engine import GoStopEngine
from rl.action_space import apply_action, legal_action_mask

MAX_STEPS_PER_EPISODE = 500

# Seed base for held-out evaluation deals: far above anything training-time evals used, so no
# reported final number was ever measured on a deal a run saw in its own logging.
HELDOUT_EVAL_SEED = 1_000_000


def wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a win rate. Preferred over the naive
    p +/- z*sqrt(p(1-p)/n) because it stays inside [0, 1] and behaves sensibly at
    small n and extreme rates -- exactly the regime a 30-game checkpoint eval is in."""
    if n == 0:
        return (0.0, 1.0)
    p = successes / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def episode_setup(i: int) -> tuple[bool, int]:
    """(policy_is_seat_1, dealer) for evaluation episode i.

    Seat and dealer must vary *independently*. The first mover is (dealer + 1) % 2, so if seat and
    dealer both flip every episode (as an earlier version did) they cancel and the policy under
    test moves second in every single game. Cycling through all four combinations puts it first in
    exactly half the games and second in the other half."""
    return i % 2 == 1, (i // 2) % 2


def play_episode(policy_a, policy_b, seed: int, dealer: int = 0):
    """policy_a plays seat 0, policy_b plays seat 1. Returns the hand's HandResult."""
    engine = GoStopEngine(num_players=2, dealer=dealer, rng=random.Random(seed))
    policies = [policy_a, policy_b]
    steps = 0
    while not engine.state.hand_over:
        steps += 1
        if steps > MAX_STEPS_PER_EPISODE:
            raise RuntimeError(f"episode did not terminate within {MAX_STEPS_PER_EPISODE} steps")
        turn = engine.state.turn
        legal = np.flatnonzero(legal_action_mask(engine))
        action = policies[turn](engine, legal)
        apply_action(engine, int(action))
    return engine.state.result


def run_match(policy_a, policy_b, num_episodes: int, base_seed: int = 0) -> dict:
    """Runs num_episodes, cycling seat and dealer independently (see episode_setup) so the policy
    under test moves first in half the games and second in the other half. Returns win/nagari
    counts from policy_a's perspective."""
    wins_a = wins_b = nagari = 0
    for i in range(num_episodes):
        swapped, dealer = episode_setup(i)
        seat_a_policy, seat_b_policy = (policy_b, policy_a) if swapped else (policy_a, policy_b)
        result = play_episode(seat_a_policy, seat_b_policy, seed=base_seed + i, dealer=dealer)
        if result.nagari:
            nagari += 1
            continue
        a_won = (result.winner == 1) if swapped else (result.winner == 0)
        wins_a += int(a_won)
        wins_b += int(not a_won)
    return {
        "episodes": num_episodes, "wins_a": wins_a, "wins_b": wins_b, "nagari": nagari,
        "win_rate_a": wins_a / num_episodes, "win_rate_b": wins_b / num_episodes,
    }


if __name__ == "__main__":
    from rl.baselines.heuristic_agent import heuristic_policy
    from rl.baselines.random_agent import random_policy

    stats = run_match(heuristic_policy, random_policy, num_episodes=1000)
    print(stats)
