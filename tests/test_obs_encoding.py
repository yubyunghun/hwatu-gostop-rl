import numpy as np

from rl.obs_encoding import OBS_SIZE, encode
from tests.conftest import make_engine

M5_ANIMAL, M5_RIBBON, M5_PI_A, M5_PI_B = 16, 17, 18, 19


def test_encode_shape_and_dtype():
    engine = make_engine(hands=[{M5_ANIMAL}, {M5_RIBBON}])
    obs = encode(engine)
    assert obs.shape == (OBS_SIZE,)
    assert obs.dtype == np.float32


def test_own_hand_reflects_the_acting_player_not_a_fixed_index():
    # "own hand" occupies obs[0:48]. It must always describe engine.state.turn's
    # hand, not a fixed absolute player index, so one network can play both seats.
    engine = make_engine(hands=[{M5_ANIMAL}, {M5_RIBBON}], turn=0)
    obs0 = encode(engine)
    assert obs0[M5_ANIMAL] == 1.0
    assert obs0[M5_RIBBON] == 0.0

    engine.state.turn = 1
    obs1 = encode(engine)
    assert obs1[M5_ANIMAL] == 0.0
    assert obs1[M5_RIBBON] == 1.0


def test_unseen_excludes_hand_field_and_both_captured_piles():
    engine = make_engine(hands=[{M5_ANIMAL}, {M5_RIBBON}], field_ids=[M5_PI_A])
    engine.state.players[0].captured = [M5_PI_B]
    obs = encode(engine)
    unseen_offset = 48 * 4
    # M5_ANIMAL is player 0's own hand -> not unseen
    assert obs[unseen_offset + M5_ANIMAL] == 0.0
    # M5_PI_A is on the field -> not unseen
    assert obs[unseen_offset + M5_PI_A] == 0.0
    # M5_PI_B is captured (own pile) -> not unseen
    assert obs[unseen_offset + M5_PI_B] == 0.0
    # M5_RIBBON is in the opponent's hand -- genuinely unseen from player 0's perspective
    assert obs[unseen_offset + M5_RIBBON] == 1.0


def test_decision_node_onehot_and_bomb_flag_present():
    engine = make_engine(hands=[{M5_ANIMAL, M5_RIBBON, M5_PI_A}, set()], field_ids=[M5_PI_B])
    obs = encode(engine)
    decision_offset = 48 * 5 + 6
    assert obs[decision_offset:decision_offset + 3].sum() == 1.0  # exactly one decision node active
    bomb_flag_index = decision_offset + 3
    # available_bombs() reflects hand/field shape alone, independent of which
    # decision node happens to be pending -- 3-in-hand + 1-on-field qualifies here.
    assert obs[bomb_flag_index] == 1.0
