from rl.baselines.heuristic_agent import heuristic_policy
from rl.baselines.random_agent import random_policy
import pytest

from rl.evaluate import run_match, wilson_interval


def test_wilson_interval_matches_known_value():
    # 50/100 -> the standard textbook Wilson interval, roughly (0.404, 0.596).
    low, high = wilson_interval(50, 100)
    assert low == pytest.approx(0.404, abs=0.002)
    assert high == pytest.approx(0.596, abs=0.002)


def test_wilson_interval_stays_in_bounds_at_the_extremes():
    assert wilson_interval(0, 30)[0] == 0.0
    assert wilson_interval(30, 30)[1] == 1.0
    assert wilson_interval(0, 0) == (0.0, 1.0)


def test_wilson_interval_narrows_as_sample_grows():
    small = wilson_interval(9, 30)
    large = wilson_interval(90, 300)
    assert (large[1] - large[0]) < (small[1] - small[0])


def test_heuristic_clearly_beats_random():
    # Regression guard for the phase-gate result (~73% over 1000 episodes at full
    # scale): a smaller, fast sample with a conservative threshold so this stays
    # a meaningful check on capture/bomb/go-stop logic without being flaky.
    stats = run_match(heuristic_policy, random_policy, num_episodes=300, base_seed=1000)
    assert stats["win_rate_a"] > 0.55
    assert stats["win_rate_a"] > stats["win_rate_b"]
