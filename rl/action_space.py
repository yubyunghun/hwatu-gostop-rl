"""The single Discrete(51) action mapping shared by rl/env.py and (later)
api/bot_inference.py, so a trained policy's action indices mean the same thing in
training and in production.

0-47: a specific card id. Its meaning depends on the pending decision node:
  - PLAY_CARD: play this card from hand.
  - BOMB_DECISION: declare a bomb for this card's month (the specific id used is
    arbitrary -- any hand card of that month -- since the mask picks a canonical one).
Note there is no separate CAPTURE_CHOICE node: this engine's capture resolution is
fully deterministic given the played/drawn card (see RULES.md section 4), so unlike
some fishing-card games there is never a genuine multi-way capture choice to encode.
48: SKIP -- decline an available bomb.
49: GO.
50: STOP.
"""

import numpy as np

from engine.cards import month_of
from engine.engine import GoStopEngine
from engine.state import DecisionNode

ACTION_SIZE = 51
SKIP = 48
GO = 49
STOP = 50


def _month_action_id(engine: GoStopEngine, month: int) -> int:
    hand = engine.state.players[engine.state.turn].hand
    candidates = sorted(cid for cid in hand if month_of(cid) == month)
    return candidates[0]


def legal_action_mask(engine: GoStopEngine) -> np.ndarray:
    mask = np.zeros(ACTION_SIZE, dtype=bool)
    s = engine.state
    decision = s.pending_decision

    if decision == DecisionNode.PLAY_CARD:
        for cid in s.players[s.turn].hand:
            mask[cid] = True
    elif decision == DecisionNode.BOMB_DECISION:
        for month in engine.available_bombs():
            mask[_month_action_id(engine, month)] = True
        mask[SKIP] = True
    elif decision == DecisionNode.GO_STOP:
        mask[GO] = True
        mask[STOP] = True
    return mask


def apply_action(engine: GoStopEngine, action: int) -> None:
    s = engine.state
    decision = s.pending_decision

    if decision == DecisionNode.PLAY_CARD:
        engine.play_card(action)
    elif decision == DecisionNode.BOMB_DECISION:
        if action == SKIP:
            engine.skip_bomb()
        elif 0 <= action < 48:
            engine.declare_bomb(month_of(action))
        else:
            raise ValueError(f"illegal action {action} for BOMB_DECISION")
    elif decision == DecisionNode.GO_STOP:
        if action == GO:
            engine.go()
        elif action == STOP:
            engine.stop()
        else:
            raise ValueError(f"illegal action {action} for GO_STOP")
    else:
        raise ValueError(f"no legal actions for pending_decision={decision}")
