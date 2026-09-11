"""A simple, non-learned baseline: greedy capture-value maximization for card
plays, always bomb when available, and a crude score/risk threshold for go/stop.
Used both as an evaluation anchor and (later) as a training-league member -- a
learned policy should clearly and increasingly beat this before it means anything.
"""

import numpy as np

from engine.cards import Category, card, month_of
from engine.engine import GoStopEngine
from engine.go_stop import current_raw_score
from engine.state import DecisionNode
from rl.action_space import GO, STOP

_CATEGORY_VALUE = {Category.GWANG: 4, Category.ANIMAL: 3, Category.RIBBON: 2, Category.JUNK: 1}

_MAX_GO_COUNT = 2
_STOP_DECK_REMAINING = 2
_STOP_SCORE_TOTAL = 15


def _card_value(card_id: int) -> int:
    return _CATEGORY_VALUE[card(card_id).category]


def _choose_play_card(engine: GoStopEngine) -> int:
    s = engine.state
    hand = s.players[s.turn].hand
    best_card, best_score = None, None
    for cid in hand:
        pile_len = len(s.field.get(month_of(cid), []))
        if pile_len >= 1:
            # Capturing play: prefer the largest, most valuable capture.
            captured_ids = s.field[month_of(cid)] + [cid]
            score = 1000 + sum(_card_value(c) for c in captured_ids) + 10 * pile_len
        else:
            # Dump: prefer discarding the least valuable card.
            score = -_card_value(cid)
        if best_score is None or score > best_score:
            best_card, best_score = cid, score
    return best_card


def _choose_bomb(engine: GoStopEngine) -> int | None:
    bombs = engine.available_bombs()
    return bombs[0] if bombs else None


def _choose_go_stop(engine: GoStopEngine) -> int:
    s = engine.state
    me = s.turn
    if s.players[me].go_count >= _MAX_GO_COUNT:
        return STOP
    if len(s.deck) <= _STOP_DECK_REMAINING:
        return STOP
    if current_raw_score(s, me).total >= _STOP_SCORE_TOTAL:
        return STOP
    return GO


def heuristic_policy(engine: GoStopEngine, legal_actions: np.ndarray) -> int:
    decision = engine.state.pending_decision
    if decision == DecisionNode.PLAY_CARD:
        return _choose_play_card(engine)
    if decision == DecisionNode.BOMB_DECISION:
        month = _choose_bomb(engine)
        if month is None:
            from rl.action_space import SKIP
            return SKIP
        hand = engine.state.players[engine.state.turn].hand
        return min(cid for cid in hand if month_of(cid) == month)
    if decision == DecisionNode.GO_STOP:
        return _choose_go_stop(engine)
    raise ValueError(f"heuristic_policy called with no legal decision: {decision}")
