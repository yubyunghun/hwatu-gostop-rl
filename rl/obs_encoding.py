"""Pure GameState -> np.ndarray encoding. Egocentric: "own" always means the
currently-acting player (engine.state.turn), "opponent" the other seat -- never a
fixed absolute player index -- so one policy network can play both seats in
self-play without confusion. No hidden information leaks: the opponent's hand is
never encoded directly, only merged into a combined "unseen" (deck + opponent hand)
multi-hot, matching what the acting player could actually infer from public state.
"""

import numpy as np

from engine.engine import GoStopEngine
from engine.go_stop import current_raw_score
from engine.state import DecisionNode

DECK_NORM = 22.0
HAND_NORM = 10.0
SCORE_NORM = 20.0

_DECISION_NODES = (DecisionNode.PLAY_CARD, DecisionNode.BOMB_DECISION, DecisionNode.GO_STOP)

NUM_SCALARS = 6
OBS_SIZE = 48 * 5 + NUM_SCALARS + len(_DECISION_NODES) + 1


def _multi_hot(card_ids) -> np.ndarray:
    v = np.zeros(48, dtype=np.float32)
    for cid in card_ids:
        v[cid] = 1.0
    return v


def encode(engine: GoStopEngine) -> np.ndarray:
    s = engine.state
    me = s.turn
    opp = s.opponents(me)[0]

    own_hand_ids = s.players[me].hand
    field_ids = s.field_cards()
    own_captured_ids = s.players[me].captured
    opp_captured_ids = s.players[opp].captured

    accounted = set(own_hand_ids) | set(field_ids) | set(own_captured_ids) | set(opp_captured_ids)
    unseen_ids = [cid for cid in range(48) if cid not in accounted]

    own_raw = current_raw_score(s, me)
    opp_raw = current_raw_score(s, opp)

    scalars = np.array([
        len(s.deck) / DECK_NORM,
        len(s.players[opp].hand) / HAND_NORM,
        float(s.players[me].go_count),
        float(s.players[opp].go_count),
        own_raw.total / SCORE_NORM,
        opp_raw.total / SCORE_NORM,
    ], dtype=np.float32)

    decision_onehot = np.zeros(len(_DECISION_NODES), dtype=np.float32)
    if s.pending_decision in _DECISION_NODES:
        decision_onehot[_DECISION_NODES.index(s.pending_decision)] = 1.0

    bomb_flag = np.array([1.0 if engine.available_bombs() else 0.0], dtype=np.float32)

    return np.concatenate([
        _multi_hot(own_hand_ids), _multi_hot(field_ids), _multi_hot(own_captured_ids),
        _multi_hot(opp_captured_ids), _multi_hot(unseen_ids), scalars, decision_onehot, bomb_flag,
    ])
