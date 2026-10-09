import pytest

from engine.capture import resolve_capture_choice, resolve_draw, resolve_hand_play
from engine.state import DecisionNode, EventType
from tests.conftest import make_state

# Month 5 (Iris): ids 16=animal, 17=ribbon(chodan), 18=pi, 19=pi -- a "plain" month with
# no godori/ssangpi flags, used as the default test month throughout.
M5_ANIMAL, M5_RIBBON, M5_PI_A, M5_PI_B = 16, 17, 18, 19
DECOY = 30  # month 8 pi card, used to keep the field non-empty when a test isn't about sweeps
UNRELATED = 10  # month 3 pi card, matches neither month 5 nor the decoy's month 8


def test_zero_match_adds_to_field():
    state = make_state(hands=[{M5_ANIMAL}, set()])
    resolve_hand_play(state, 0, M5_ANIMAL)
    assert state.players[0].hand == set()
    assert state.field[5] == [M5_ANIMAL]
    assert state.events[-1].type == EventType.FIELD_ADD


def test_one_match_defers_capture_until_draw_resolves():
    state = make_state(hands=[{M5_ANIMAL}, set()], field_ids=[M5_RIBBON, DECOY])
    resolve_hand_play(state, 0, M5_ANIMAL)
    assert state.pending_pair == (M5_ANIMAL, M5_RIBBON)
    assert state.field[5] == [M5_RIBBON, M5_ANIMAL]
    assert state.players[0].captured == []  # not captured yet


def test_one_match_then_non_matching_draw_finalizes_capture():
    state = make_state(hands=[{M5_ANIMAL}, set()], field_ids=[M5_RIBBON, DECOY])
    resolve_hand_play(state, 0, M5_ANIMAL)
    resolve_draw(state, 0, UNRELATED)  # month 3 pi card -> unrelated to both month 5 and the decoy
    assert state.pending_pair is None
    assert sorted(state.players[0].captured) == sorted([M5_ANIMAL, M5_RIBBON])
    assert 5 not in state.field


def test_one_match_then_same_month_draw_is_ppeok():
    state = make_state(hands=[{M5_ANIMAL}, set()], field_ids=[M5_RIBBON, DECOY])
    resolve_hand_play(state, 0, M5_ANIMAL)
    resolve_draw(state, 0, M5_PI_A)  # also month 5 -> ppeok
    assert state.pending_pair is None
    assert state.players[0].captured == []  # locked, not captured
    assert sorted(state.field[5]) == sorted([M5_RIBBON, M5_ANIMAL, M5_PI_A])
    ppeok_events = [e for e in state.events if e.type == EventType.PPEOK_LOCK]
    assert len(ppeok_events) == 1
    assert state.players[0].bonus_pi_received == 1
    assert state.players[1].bonus_pi_paid == 1


def test_two_match_defers_to_a_capture_choice_instead_of_auto_capturing():
    # RULES.md #4 (pagat): "If there are two cards of this month in the layout, you can choose on
    # which one you will place your played card" -- not an automatic capture-all-3.
    state = make_state(hands=[{M5_PI_A}, set()], field_ids=[M5_ANIMAL, M5_RIBBON, DECOY])
    resolve_hand_play(state, 0, M5_PI_A)
    assert state.players[0].captured == []  # nothing captured yet
    assert state.pending_decision == DecisionNode.CAPTURE_CHOICE
    assert state.pending_capture_choice == (M5_PI_A, (M5_ANIMAL, M5_RIBBON))
    assert state.capture_choice_after_draw is False
    assert sorted(state.field[5]) == sorted([M5_ANIMAL, M5_RIBBON, M5_PI_A])  # all 3 sit together


def test_capture_choice_from_hand_play_defers_as_a_pending_pair():
    state = make_state(hands=[{M5_PI_A}, set()], field_ids=[M5_ANIMAL, M5_RIBBON, DECOY])
    resolve_hand_play(state, 0, M5_PI_A)
    resolve_capture_choice(state, player=0, chosen_field_card_id=M5_ANIMAL)
    assert state.pending_pair == (M5_PI_A, M5_ANIMAL)
    assert state.players[0].captured == []  # still not captured -- waiting on the forced draw
    assert sorted(state.field[5]) == sorted([M5_ANIMAL, M5_RIBBON, M5_PI_A])  # unchosen stays put


def test_capture_choice_then_non_matching_draw_captures_only_the_chosen_pair():
    state = make_state(hands=[{M5_PI_A}, set()], field_ids=[M5_ANIMAL, M5_RIBBON, DECOY])
    resolve_hand_play(state, 0, M5_PI_A)
    resolve_capture_choice(state, player=0, chosen_field_card_id=M5_ANIMAL)
    resolve_draw(state, 0, UNRELATED)  # month 3, matches neither
    assert state.pending_pair is None
    assert sorted(state.players[0].captured) == sorted([M5_PI_A, M5_ANIMAL])
    assert state.field[5] == [M5_RIBBON]  # unchosen card left behind as its own ordinary 1-card pile
    assert state.field.get(8) == [DECOY]  # decoy untouched
    assert state.field.get(3) == [UNRELATED]


def test_capture_choice_then_matching_draw_captures_all_four_not_a_ppeok():
    # pagat: "If your played card matched two layout cards and the stock card is also that month,
    # you capture all four cards of this month." Not a ppeok lock -- that's specifically the 3-stuck
    # case, and here there's a 4th card, so the whole thing resolves as a capture instead.
    state = make_state(hands=[{M5_PI_A}, set()], field_ids=[M5_ANIMAL, M5_RIBBON, DECOY])
    resolve_hand_play(state, 0, M5_PI_A)
    resolve_capture_choice(state, player=0, chosen_field_card_id=M5_ANIMAL)
    resolve_draw(state, 0, M5_PI_B)  # the 4th month-5 card
    assert state.pending_pair is None
    assert sorted(state.players[0].captured) == sorted([M5_PI_A, M5_ANIMAL, M5_RIBBON, M5_PI_B])
    assert 5 not in state.field
    assert not any(e.type == EventType.PPEOK_LOCK for e in state.events)
    assert any(e.type == EventType.CAPTURE for e in state.events)


def test_capture_choice_rejects_an_illegal_target():
    state = make_state(hands=[{M5_PI_A}, set()], field_ids=[M5_ANIMAL, M5_RIBBON, DECOY])
    resolve_hand_play(state, 0, M5_PI_A)
    with pytest.raises(ValueError):
        resolve_capture_choice(state, player=0, chosen_field_card_id=DECOY)  # not one of the 2 candidates


def test_drawn_card_matching_two_field_cards_also_defers_to_a_choice():
    # Symmetric with the hand-play case: the drawn card is just as much a single card being placed
    # against the layout. No pending_pair exists here, so resolve_draw reaches the bottom section.
    state = make_state(hands=[{DECOY}, set()], field_ids=[M5_ANIMAL, M5_RIBBON])
    resolve_draw(state, 0, M5_PI_A)
    assert state.players[0].captured == []
    assert state.pending_decision == DecisionNode.CAPTURE_CHOICE
    assert state.pending_capture_choice == (M5_PI_A, (M5_ANIMAL, M5_RIBBON))
    assert state.capture_choice_after_draw is True


def test_capture_choice_from_a_draw_resolves_immediately_no_further_draw_to_wait_on():
    state = make_state(hands=[{DECOY}, set()], field_ids=[M5_ANIMAL, M5_RIBBON])
    resolve_draw(state, 0, M5_PI_A)
    resolve_capture_choice(state, player=0, chosen_field_card_id=M5_RIBBON)
    assert state.pending_pair is None  # nothing left pending -- it captured right away
    assert sorted(state.players[0].captured) == sorted([M5_PI_A, M5_RIBBON])
    assert state.field[5] == [M5_ANIMAL]  # unchosen left behind


def test_three_match_completes_a_locked_pile():
    state = make_state(hands=[{M5_PI_B}, set()], field_ids=[M5_ANIMAL, M5_RIBBON, M5_PI_A])
    resolve_hand_play(state, 0, M5_PI_B)
    assert sorted(state.players[0].captured) == sorted([M5_ANIMAL, M5_RIBBON, M5_PI_A, M5_PI_B])
    assert 5 not in state.field


def test_capture_that_empties_the_field_triggers_sweep_bonus():
    state = make_state(hands=[{M5_PI_A}, set()], field_ids=[M5_ANIMAL, M5_RIBBON])
    resolve_hand_play(state, 0, M5_PI_A)
    resolve_capture_choice(state, player=0, chosen_field_card_id=M5_ANIMAL)
    resolve_draw(state, 0, M5_PI_B)  # the 4th month-5 card -- empties the field entirely
    assert state.field == {}
    assert any(e.type == EventType.SWEEP for e in state.events)
    # sweep penalty stacks on top of the capture's own (zero, in this case) penalty
    assert state.players[0].bonus_pi_received == 1
    assert state.players[1].bonus_pi_paid == 1


def test_capture_choice_resolving_immediately_can_also_trigger_sweep():
    state = make_state(hands=[{DECOY}, set()], field_ids=[M5_ANIMAL, M5_RIBBON])
    resolve_draw(state, 0, M5_PI_A)
    resolve_capture_choice(state, player=0, chosen_field_card_id=M5_ANIMAL)
    # the unchosen card (M5_RIBBON) is still on the field, so no sweep yet
    assert not any(e.type == EventType.SWEEP for e in state.events)
    assert state.field[5] == [M5_RIBBON]
