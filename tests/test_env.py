import numpy as np

from engine.state import DecisionNode
from rl.action_space import legal_action_mask
from rl.env import GoStopEnv
from rl.obs_encoding import OBS_SIZE


def _random_full_episode(seed: int):
    env = GoStopEnv(seed=seed)
    obs, info = env.reset(seed=seed)
    rng = np.random.default_rng(seed)
    total_steps = 0
    terminated = truncated = False
    while not (terminated or truncated):
        total_steps += 1
        assert total_steps < 300, "episode did not terminate"
        mask = env.action_masks()
        legal = np.flatnonzero(mask)
        assert len(legal) > 0
        action = int(rng.choice(legal))
        obs, reward, terminated, truncated, info = env.step(action)
        assert obs.shape == (OBS_SIZE, )
    return env, obs, reward


def test_reset_returns_correctly_shaped_observation():
    env = GoStopEnv(seed=0)
    obs, info = env.reset(seed=0)
    assert obs.shape == (OBS_SIZE,)
    assert env.engine.state.turn == env.learner_seat  # opponent turns were fast-forwarded


def test_episodes_terminate_across_many_seeds():
    for seed in range(30):
        env, obs, reward = _random_full_episode(seed)
        assert env.engine.state.hand_over
        assert isinstance(reward, float)


def test_reward_matches_engine_result_scaled():
    env, obs, reward = _random_full_episode(7)
    result = env.engine.state.result
    if result.nagari:
        assert reward == 0.0
    else:
        expected = result.scores[env.learner_seat] / 40.0
        assert reward == expected


def test_action_masks_never_empty_mid_episode():
    env = GoStopEnv(seed=1)
    env.reset(seed=1)
    rng = np.random.default_rng(1)
    for _ in range(100):
        if env.engine.state.hand_over:
            break
        mask = env.action_masks()
        assert mask.any()
        legal = np.flatnonzero(mask)
        env.step(int(rng.choice(legal)))


def test_env_step_matches_raw_engine_for_a_scripted_sequence():
    # Drive the same seed through the raw engine directly and through the env
    # wrapper (using a policy that mimics "always pick the lowest legal id"), and
    # confirm they reach byte-identical final state -- the wrapper must not add
    # any hidden divergence from the engine it wraps.
    from engine.engine import GoStopEngine
    import random as pyrandom

    def lowest_id_policy(engine, legal_actions):
        # Mirrors the raw_engine loop below exactly: lowest hand card, always skip
        # bombs, always stop -- so both drivers make identical decisions throughout.
        from rl.action_space import SKIP, STOP
        decision = engine.state.pending_decision
        if decision == DecisionNode.BOMB_DECISION:
            return SKIP
        if decision == DecisionNode.GO_STOP:
            return STOP
        return int(min(legal_actions))

    raw_engine = GoStopEngine(num_players=2, dealer=0, rng=pyrandom.Random(99))
    while not raw_engine.state.hand_over:
        decision = raw_engine.state.pending_decision
        if decision == DecisionNode.PLAY_CARD:
            raw_engine.play_card(min(raw_engine.state.players[raw_engine.state.turn].hand))
        elif decision == DecisionNode.BOMB_DECISION:
            raw_engine.skip_bomb()
        elif decision == DecisionNode.GO_STOP:
            raw_engine.stop()

    from rl.action_space import SKIP, STOP

    env = GoStopEnv(opponent_policy=lowest_id_policy, seed=0)
    env.engine = GoStopEngine(num_players=2, dealer=0, rng=pyrandom.Random(99))
    env.learner_seat = env.engine.state.turn
    env._run_opponent_turns()  # no-op here since learner_seat is already the mover
    while not env.engine.state.hand_over:
        mask = legal_action_mask(env.engine)
        legal = np.flatnonzero(mask)
        decision = env.engine.state.pending_decision
        if decision == DecisionNode.PLAY_CARD:
            action = int(min(legal))
        elif decision == DecisionNode.BOMB_DECISION:
            action = SKIP
        else:  # GO_STOP
            action = STOP
        env.step(action)

    assert env.engine.state.result == raw_engine.state.result
