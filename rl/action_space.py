"""The single Discrete(ACTION_SIZE) action mapping shared by rl/env.py and
api/bot_inference.py, so a trained policy's action indices mean the same thing in
training and in production.

0 to NUM_CARDS-1: a specific card id. Its meaning depends on the pending decision node:
  - PLAY_CARD: play this card from hand.
  - BOMB_DECISION: declare a bomb for this card's month (the specific id used is
    arbitrary -- any hand card of that month -- since the mask picks a canonical one).
Note there is no separate CAPTURE_CHOICE node: this engine's capture resolution is
fully deterministic given the played/drawn card (see RULES.md section 4), so unlike
some fishing-card games there is never a genuine multi-way capture choice to encode.
A bonus card id (RULES.md #12), if any exist, is never legal at either of the two nodes above -- it's
always resolved out of a hand before PLAY_CARD/BOMB_DECISION is reached (GoStopEngine._resolve_bonus_cards_in_hand).
NUM_CARDS: SKIP -- decline an available bomb.
NUM_CARDS + 1: GO.
NUM_CARDS + 2: STOP.

SKIP/GO/STOP sit right after every card id rather than at fixed indices 48/49/50, so enabling bonus
cards (which grows NUM_CARDS) can never collide a real card id with one of these. At the default
NUM_BONUS_CARDS = 0, NUM_CARDS is 48 and these come out to the same 48/49/50 as always, so this is a
no-op for every existing checkpoint.
"""

import numpy as np

from engine.cards import NUM_CARDS, month_of
from engine.engine import GoStopEngine
from engine.state import DecisionNode

SKIP = NUM_CARDS
GO = NUM_CARDS + 1
STOP = NUM_CARDS + 2
ACTION_SIZE = NUM_CARDS + 3


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
        elif 0 <= action < NUM_CARDS:
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
