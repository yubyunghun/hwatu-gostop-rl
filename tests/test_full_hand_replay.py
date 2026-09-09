"""End-to-end sanity check: drive full hands through GoStopEngine with simple
deterministic policies and assert the invariants that must hold no matter what
sequence of bombs/ppeoks/ttadaks/sweeps/go-stops occurred -- card conservation
above all. Exact point totals for specific real-game example hands are pinned
instead at the unit level in test_scoring.py, against RULES.md section 8."""

import random

from engine.engine import GoStopEngine
from engine.state import DecisionNode


def _all_accounted_cards(engine: GoStopEngine) -> list[int]:
    s = engine.state
    ids: list[int] = []
    for p in s.players:
        ids.extend(p.hand)
        ids.extend(p.captured)
    ids.extend(s.field_cards())
    ids.extend(s.deck)
    return ids


def _play_one_full_hand(seed: int) -> GoStopEngine:
    rng = random.Random(seed)
    engine = GoStopEngine(num_players=2, dealer=0, rng=random.Random(seed))
    steps = 0
    while not engine.state.hand_over:
        steps += 1
        assert steps < 500, "hand did not terminate -- possible infinite loop"
        assert sorted(_all_accounted_cards(engine)) == list(range(48))

        decision = engine.state.pending_decision
        if decision == DecisionNode.BOMB_DECISION:
            bombs = engine.available_bombs()
            if bombs and rng.random() < 0.5:
                engine.declare_bomb(bombs[0])
            else:
                engine.skip_bomb()
        elif decision == DecisionNode.PLAY_CARD:
            hand = sorted(engine.state.players[engine.state.turn].hand)
            engine.play_card(rng.choice(hand))
        elif decision == DecisionNode.GO_STOP:
            if rng.random() < 0.5:
                engine.go()
            else:
                engine.stop()
        else:
            raise AssertionError(f"unexpected pending decision: {decision}")
    return engine


def test_full_hand_runs_to_completion_and_conserves_all_48_cards():
    for seed in range(100):
        engine = _play_one_full_hand(seed)
        assert engine.state.hand_over
        assert engine.state.pending_decision == DecisionNode.HAND_OVER
        assert sorted(_all_accounted_cards(engine)) == list(range(48))


def test_full_hand_result_is_either_a_single_winner_or_nagari():
    for seed in range(100):
        engine = _play_one_full_hand(seed)
        result = engine.state.result
        assert result is not None
        if result.nagari:
            assert result.winner is None
            assert all(s == 0 for s in result.scores)
        else:
            assert result.winner in (0, 1)
            loser = 1 - result.winner
            assert result.scores[result.winner] > 0
            assert result.scores[loser] == -result.scores[result.winner]


def test_full_hand_is_deterministic_given_the_same_seed():
    engine_a = _play_one_full_hand(12345)
    engine_b = _play_one_full_hand(12345)
    assert engine_a.state.result == engine_b.state.result
