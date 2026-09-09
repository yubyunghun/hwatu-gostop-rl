import pytest

from engine.bombs import available_bomb_months, resolve_bomb
from engine.state import EventType
from tests.conftest import make_state

M5_ANIMAL, M5_RIBBON, M5_PI_A, M5_PI_B = 16, 17, 18, 19


def test_available_bomb_months_requires_three_in_hand_and_one_on_field():
    state = make_state(hands=[{M5_ANIMAL, M5_RIBBON, M5_PI_A}, set()], field_ids=[M5_PI_B])
    assert available_bomb_months(state, 0) == [5]


def test_no_bomb_available_without_three_in_hand():
    state = make_state(hands=[{M5_ANIMAL, M5_RIBBON}, set()], field_ids=[M5_PI_A, M5_PI_B])
    assert available_bomb_months(state, 0) == []


def test_no_bomb_available_if_field_has_zero_or_more_than_one():
    state = make_state(hands=[{M5_ANIMAL, M5_RIBBON, M5_PI_A}, set()], field_ids=[])
    assert available_bomb_months(state, 0) == []


def test_resolve_bomb_captures_all_four_and_pays_penalty():
    state = make_state(hands=[{M5_ANIMAL, M5_RIBBON, M5_PI_A}, set()], field_ids=[M5_PI_B])
    resolve_bomb(state, 0, 5)
    assert sorted(state.players[0].captured) == sorted([M5_ANIMAL, M5_RIBBON, M5_PI_A, M5_PI_B])
    assert state.players[0].hand == set()
    assert 5 not in state.field
    assert any(e.type == EventType.BOMB for e in state.events)
    # this bomb also empties the field, so the bonus stacks: 1 for the bomb + 1 for the sweep
    assert any(e.type == EventType.SWEEP for e in state.events)
    assert state.players[0].bonus_pi_received == 2
    assert state.players[1].bonus_pi_paid == 2


def test_resolve_bomb_rejects_illegal_declaration():
    state = make_state(hands=[{M5_ANIMAL, M5_RIBBON}, set()], field_ids=[M5_PI_A, M5_PI_B])
    with pytest.raises(ValueError):
        resolve_bomb(state, 0, 5)
