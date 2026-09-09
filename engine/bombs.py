"""Bomb (폭탄) declaration and resolution. See RULES.md section 7 -- BOMB_MODE is pinned
to THREE_IN_HAND_PLUS_FIELD: 3 hand cards of a month plus the field's lone 4th card."""

from engine.cards import month_of
from engine.rules_config import BOMB_PENALTY_PI
from engine.state import EventType, GameState
from engine.capture import finalize_capture  # reuse so sweep-checking stays centralized


def available_bomb_months(state: GameState, player: int) -> list[int]:
    hand = state.players[player].hand
    by_month: dict[int, int] = {}
    for cid in hand:
        by_month[month_of(cid)] = by_month.get(month_of(cid), 0) + 1
    return [m for m, count in by_month.items() if count >= 3 and len(state.field.get(m, [])) == 1]


def resolve_bomb(state: GameState, player: int, month: int) -> None:
    hand = state.players[player].hand
    hand_cards = [cid for cid in hand if month_of(cid) == month]
    if len(hand_cards) < 3 or len(state.field.get(month, [])) != 1:
        raise ValueError(f"player {player} cannot bomb month {month}")
    hand_cards = hand_cards[:3]
    field_card = state.field[month][0]

    for cid in hand_cards:
        hand.discard(cid)
    state.field.pop(month, None)
    finalize_capture(state, player, hand_cards + [field_card], EventType.BOMB,
                       pi_per_opponent=BOMB_PENALTY_PI)
