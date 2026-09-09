from engine.capture import resolve_draw, resolve_hand_play
from engine.state import EventType
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


def test_two_match_captures_immediately_and_watches_for_ttadak():
    state = make_state(hands=[{M5_PI_A}, set()], field_ids=[M5_ANIMAL, M5_RIBBON, DECOY])
    resolve_hand_play(state, 0, M5_PI_A)
    assert sorted(state.players[0].captured) == sorted([M5_ANIMAL, M5_RIBBON, M5_PI_A])
    assert state.ttadak_watch_month == 5
    assert 5 not in state.field


def test_ttadak_completes_on_matching_draw():
    state = make_state(hands=[{M5_PI_A}, set()], field_ids=[M5_ANIMAL, M5_RIBBON, DECOY])
    resolve_hand_play(state, 0, M5_PI_A)
    resolve_draw(state, 0, M5_PI_B)  # last month-5 card
    assert sorted(state.players[0].captured) == sorted([M5_ANIMAL, M5_RIBBON, M5_PI_A, M5_PI_B])
    assert any(e.type == EventType.TTADAK for e in state.events)
    assert state.players[0].bonus_pi_received == 1
    assert state.players[1].bonus_pi_paid == 1


def test_ttadak_watch_clears_on_non_matching_draw():
    state = make_state(hands=[{M5_PI_A}, set()], field_ids=[M5_ANIMAL, M5_RIBBON, DECOY])
    resolve_hand_play(state, 0, M5_PI_A)
    resolve_draw(state, 0, UNRELATED)  # unrelated month, no ttadak
    assert state.ttadak_watch_month is None
    assert not any(e.type == EventType.TTADAK for e in state.events)
    assert state.field.get(8) == [DECOY]  # decoy untouched
    assert state.field.get(3) == [UNRELATED]  # unrelated draw added under its own month


def test_three_match_completes_a_locked_pile():
    state = make_state(hands=[{M5_PI_B}, set()], field_ids=[M5_ANIMAL, M5_RIBBON, M5_PI_A])
    resolve_hand_play(state, 0, M5_PI_B)
    assert sorted(state.players[0].captured) == sorted([M5_ANIMAL, M5_RIBBON, M5_PI_A, M5_PI_B])
    assert 5 not in state.field


def test_capture_that_empties_the_field_triggers_sweep_bonus():
    state = make_state(hands=[{M5_PI_A}, set()], field_ids=[M5_ANIMAL, M5_RIBBON])
    resolve_hand_play(state, 0, M5_PI_A)
    assert state.field == {}
    assert any(e.type == EventType.SWEEP for e in state.events)
    # sweep penalty stacks on top of the capture's own (zero, in this case) penalty
    assert state.players[0].bonus_pi_received == 1
    assert state.players[1].bonus_pi_paid == 1
