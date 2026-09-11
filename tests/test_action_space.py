import numpy as np

from engine.state import DecisionNode
from rl.action_space import ACTION_SIZE, GO, SKIP, STOP, apply_action, legal_action_mask
from tests.conftest import make_engine

M5_ANIMAL, M5_RIBBON, M5_PI_A, M5_PI_B = 16, 17, 18, 19


def test_play_card_mask_matches_hand():
    engine = make_engine(hands=[{M5_ANIMAL, M5_RIBBON}, set()])
    mask = legal_action_mask(engine)
    assert mask.shape == (ACTION_SIZE,)
    assert set(np.flatnonzero(mask)) == {M5_ANIMAL, M5_RIBBON}


def test_bomb_decision_mask_includes_skip_and_one_id_per_bombable_month():
    engine = make_engine(hands=[{M5_ANIMAL, M5_RIBBON, M5_PI_A}, set()], field_ids=[M5_PI_B])
    engine.state.pending_decision = DecisionNode.BOMB_DECISION
    mask = legal_action_mask(engine)
    legal = set(np.flatnonzero(mask))
    assert SKIP in legal
    assert len(legal) == 2  # SKIP + exactly one card id representing the month-5 bomb
    assert legal - {SKIP} <= {M5_ANIMAL, M5_RIBBON, M5_PI_A}


def test_go_stop_mask_is_exactly_go_and_stop():
    engine = make_engine(hands=[set(), set()])
    engine.state.pending_decision = DecisionNode.GO_STOP
    mask = legal_action_mask(engine)
    assert set(np.flatnonzero(mask)) == {GO, STOP}


def test_apply_action_play_card_removes_from_hand():
    engine = make_engine(hands=[{M5_ANIMAL}, set()])
    apply_action(engine, M5_ANIMAL)
    assert M5_ANIMAL not in engine.state.players[0].hand


def test_apply_action_bomb_skip_falls_through_to_play_card():
    engine = make_engine(hands=[{M5_ANIMAL, M5_RIBBON, M5_PI_A}, set()], field_ids=[M5_PI_B])
    engine.state.pending_decision = DecisionNode.BOMB_DECISION
    apply_action(engine, SKIP)
    assert engine.state.pending_decision == DecisionNode.PLAY_CARD


def test_apply_action_bomb_declares_and_captures():
    engine = make_engine(hands=[{M5_ANIMAL, M5_RIBBON, M5_PI_A}, set()], field_ids=[M5_PI_B], deck=[])
    engine.state.pending_decision = DecisionNode.BOMB_DECISION
    apply_action(engine, M5_ANIMAL)  # any month-5 hand card id declares the month-5 bomb
    assert sorted(engine.state.players[0].captured) == sorted([M5_ANIMAL, M5_RIBBON, M5_PI_A, M5_PI_B])


def test_apply_action_go_increments_go_count():
    # player 1 needs a card to play next, otherwise advancing the turn would run
    # straight into hand-exhaustion auto-settlement instead of a plain PLAY_CARD turn.
    engine = make_engine(hands=[set(), {12}], deck=[13])
    engine.state.players[0].captured = [0, 8, 28, 40, 44]  # 15-point hand for player 0
    engine.state.pending_decision = DecisionNode.GO_STOP
    engine.state.scoring_player = 0
    apply_action(engine, GO)
    assert engine.state.players[0].go_count == 1
    assert engine.state.pending_decision == DecisionNode.PLAY_CARD


def test_apply_action_stop_ends_the_hand():
    engine = make_engine(hands=[set(), set()])
    engine.state.players[0].captured = [0, 8, 28, 40, 44]  # 15-point hand
    engine.state.pending_decision = DecisionNode.GO_STOP
    engine.state.scoring_player = 0
    apply_action(engine, STOP)
    assert engine.state.hand_over
    assert engine.state.result.winner == 0
