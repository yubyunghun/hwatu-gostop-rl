from engine.go_stop import (
    check_hands_exhausted_end, check_go_stop_trigger, resolve_go, resolve_stop,
)
from engine.rules_config import GO_STOP_MIN_SCORE
from engine.state import DecisionNode, EventType
from tests.conftest import make_state

FIVE_GWANG = [0, 8, 28, 40, 44]  # 15-point hand, comfortably above threshold
BELOW_THRESHOLD = [2, 3]  # 2 plain pi -> pi_count=2, score 0


def test_check_go_stop_trigger_sets_pending_decision_when_qualifying():
    state = make_state(hands=[set(), set()])
    state.players[0].captured = list(FIVE_GWANG)
    check_go_stop_trigger(state, 0)
    assert state.pending_decision == DecisionNode.GO_STOP
    assert state.scoring_player == 0


def test_check_go_stop_trigger_does_not_fire_below_threshold():
    state = make_state(hands=[set(), set()])
    state.players[0].captured = list(BELOW_THRESHOLD)
    check_go_stop_trigger(state, 0)
    assert state.pending_decision == DecisionNode.PLAY_CARD
    assert state.scoring_player is None


def test_resolve_go_increments_go_count_and_returns_to_play():
    state = make_state(hands=[set(), set()])
    state.players[0].captured = list(FIVE_GWANG)
    check_go_stop_trigger(state, 0)
    resolve_go(state)
    assert state.players[0].go_count == 1
    assert state.pending_decision == DecisionNode.PLAY_CARD
    assert state.scoring_player is None
    assert any(e.type == EventType.GO for e in state.events)


def test_resolve_stop_ends_hand_with_positive_negative_scores():
    state = make_state(hands=[set(), set()])
    state.players[0].captured = list(FIVE_GWANG)
    state.players[1].captured = list(BELOW_THRESHOLD)
    check_go_stop_trigger(state, 0)
    resolve_stop(state)
    assert state.hand_over
    assert state.pending_decision == DecisionNode.HAND_OVER
    assert state.result.winner == 0
    assert state.result.scores[0] == -state.result.scores[1]
    assert state.result.scores[0] > 0


def test_hands_exhausted_with_no_qualifier_is_nagari():
    state = make_state(hands=[set(), set()], deck=[])
    state.players[0].captured = list(BELOW_THRESHOLD)
    ended = check_hands_exhausted_end(state)
    assert ended
    assert state.hand_over
    assert state.result.nagari
    assert state.result.winner is None
    assert any(e.type == EventType.NAGARI for e in state.events)


def test_hands_exhausted_with_a_qualifier_auto_finishes_as_stop():
    state = make_state(hands=[set(), set()], deck=[])
    state.players[0].captured = list(FIVE_GWANG)
    state.players[1].captured = list(BELOW_THRESHOLD)
    ended = check_hands_exhausted_end(state)
    assert ended
    assert not state.result.nagari
    assert state.result.winner == 0


def test_hands_exhausted_check_is_noop_while_a_hand_still_has_cards():
    state = make_state(hands=[{1}, set()], deck=[])
    assert check_hands_exhausted_end(state) is False
    assert not state.hand_over


def test_hand_ends_even_with_leftover_undrawn_deck_cards():
    # Deck and hand sizes don't have to divide evenly (see engine/rules_config.py);
    # once both hands are empty the hand is over regardless of leftover deck cards.
    state = make_state(hands=[set(), set()], deck=[2])
    state.players[0].captured = list(BELOW_THRESHOLD)
    assert check_hands_exhausted_end(state) is True
    assert state.hand_over
    assert state.result.nagari


def test_go_stop_min_score_constant_is_seven():
    assert GO_STOP_MIN_SCORE == 7
