from rl.baselines.heuristic_agent import heuristic_policy
from rl.baselines.random_agent import random_policy
from rl.evaluate import run_match


def test_heuristic_clearly_beats_random():
    # Regression guard for the phase-gate result (~73% over 1000 episodes at full
    # scale): a smaller, fast sample with a conservative threshold so this stays
    # a meaningful check on capture/bomb/go-stop logic without being flaky.
    stats = run_match(heuristic_policy, random_policy, num_episodes=300, base_seed=1000)
    assert stats["win_rate_a"] > 0.55
    assert stats["win_rate_a"] > stats["win_rate_b"]
