"""Engine-level (not just bare capture.py functions) coverage of CAPTURE_CHOICE (RULES.md #4):
GoStopEngine actually pausing and resuming a turn around the decision, via play_card/choose_capture/
declare_bomb, not just the state-mutation functions underneath them."""

import pytest

from engine.state import DecisionNode
from tests.conftest import make_engine

M5_ANIMAL, M5_RIBBON, M5_PI_A, M5_PI_B = 16, 17, 18, 19
M8_GWANG, M8_ANIMAL, M8_PI_A, M8_PI_B = 28, 29, 30, 31
UNRELATED = 10  # month 3 pi card


def test_hand_play_matching_two_pauses_the_engine_at_capture_choice():
    engine = make_engine(hands=[{M5_PI_A}, set()], field_ids=[M5_ANIMAL, M5_RIBBON],
                          deck=[UNRELATED])
    engine.play_card(M5_PI_A)
    assert engine.state.pending_decision == DecisionNode.CAPTURE_CHOICE
    assert engine.state.turn == 0  # still this player's turn -- nothing advanced yet
    assert engine.legal_options() == sorted([M5_ANIMAL, M5_RIBBON])
    assert len(engine.state.deck) == 1  # the forced draw hasn't happened yet either


def test_choose_capture_rejects_an_illegal_target():
    engine = make_engine(hands=[{M5_PI_A}, set()], field_ids=[M5_ANIMAL, M5_RIBBON],
                          deck=[UNRELATED])
    engine.play_card(M5_PI_A)
    with pytest.raises(ValueError):
        engine.choose_capture(UNRELATED)


def test_other_actions_are_rejected_while_a_capture_choice_is_pending():
    engine = make_engine(hands=[{M5_PI_A}, set()], field_ids=[M5_ANIMAL, M5_RIBBON],
                          deck=[UNRELATED])
    engine.play_card(M5_PI_A)
    with pytest.raises(ValueError):
        engine.play_card(M5_PI_A)
    with pytest.raises(ValueError):
        engine.skip_bomb()
    with pytest.raises(ValueError):
        engine.go()


def test_choosing_from_the_hand_play_proceeds_to_the_forced_draw():
    engine = make_engine(hands=[{M5_PI_A}, set()], field_ids=[M5_ANIMAL, M5_RIBBON],
                          deck=[UNRELATED])
    engine.play_card(M5_PI_A)
    engine.choose_capture(M5_ANIMAL)
    assert len(engine.state.deck) == 0  # the forced draw happened as part of resuming
    assert sorted(engine.state.players[0].captured) == sorted([M5_PI_A, M5_ANIMAL])
    assert engine.state.field[5] == [M5_RIBBON]  # unchosen card left behind
    assert engine.state.pending_decision != DecisionNode.CAPTURE_CHOICE


def test_drawn_card_matching_two_also_pauses_and_resolves_without_a_further_draw():
    # Hand card (DECOY month) doesn't match anything; the forced draw is what hits the 2-card pile.
    engine = make_engine(hands=[{UNRELATED}, set()], field_ids=[M5_ANIMAL, M5_RIBBON],
                          deck=[M5_PI_A])
    engine.play_card(UNRELATED)
    assert engine.state.pending_decision == DecisionNode.CAPTURE_CHOICE
    assert engine.state.capture_choice_after_draw is True
    assert engine.legal_options() == sorted([M5_ANIMAL, M5_RIBBON])

    engine.choose_capture(M5_RIBBON)
    assert sorted(engine.state.players[0].captured) == sorted([M5_PI_A, M5_RIBBON])
    assert engine.state.field[5] == [M5_ANIMAL]
    assert engine.state.pending_decision != DecisionNode.CAPTURE_CHOICE


def test_bomb_declaration_can_still_trigger_a_capture_choice_from_its_forced_draw():
    engine = make_engine(hands=[{M5_ANIMAL, M5_RIBBON, M5_PI_A}, set()], field_ids=[M5_PI_B, 28, 29],
                          deck=[30])  # month-8 pi, lands on the pre-existing 2-card month-8 pile
    engine.state.pending_decision = DecisionNode.BOMB_DECISION  # make_engine skips _enter_turn()
    engine.declare_bomb(5)
    assert sorted(engine.state.players[0].captured) == sorted([M5_ANIMAL, M5_RIBBON, M5_PI_A, M5_PI_B])
    assert engine.state.pending_decision == DecisionNode.CAPTURE_CHOICE
    assert engine.state.capture_choice_after_draw is True
    assert engine.legal_options() == sorted([M8_GWANG, M8_ANIMAL])


def test_two_separate_capture_choices_in_one_turn_both_resolve_correctly():
    # The hand-play matches month 5's existing pair; the forced draw separately matches month 8's.
    engine = make_engine(hands=[{M5_PI_A}, set()], field_ids=[M5_ANIMAL, M5_RIBBON, M8_GWANG, M8_ANIMAL],
                          deck=[M8_PI_A])
    engine.play_card(M5_PI_A)
    assert engine.state.pending_decision == DecisionNode.CAPTURE_CHOICE
    assert engine.state.capture_choice_after_draw is False

    engine.choose_capture(M5_ANIMAL)  # resolves the hand-play's choice; triggers the forced draw
    assert sorted(engine.state.players[0].captured) == sorted([M5_PI_A, M5_ANIMAL])
    assert engine.state.field[5] == [M5_RIBBON]
    # The draw (month-8 pi) didn't match month 5 (the just-resolved pending pair's month), so it fell
    # through to the field -- which still has month 8's untouched pair, so a second choice comes up.
    assert engine.state.pending_decision == DecisionNode.CAPTURE_CHOICE
    assert engine.state.capture_choice_after_draw is True
    assert engine.legal_options() == sorted([M8_GWANG, M8_ANIMAL])

    engine.choose_capture(M8_GWANG)
    assert sorted(engine.state.players[0].captured) == sorted(
        [M5_PI_A, M5_ANIMAL, M8_PI_A, M8_GWANG])
    assert engine.state.field[8] == [M8_ANIMAL]
    assert engine.state.pending_decision != DecisionNode.CAPTURE_CHOICE
    assert len(engine.state.deck) == 0
