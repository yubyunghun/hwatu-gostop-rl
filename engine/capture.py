"""Capture resolution for a hand-play followed by its forced deck draw.

See RULES.md sections 4-6 for the mechanics this encodes. The subtle part is that a
hand-play matching exactly 1 field card is *not* finalized immediately -- it is held
as `state.pending_pair` until the following draw is known, because if that draw is
also the same month the whole trio locks as a ppeok pile instead of being captured
(section 5). A hand-play matching exactly 2 field cards *does* finalize immediately,
but marks `state.ttadak_watch_month` so the draw can be checked for ttadak (section 6).
"""

from engine.cards import month_of
from engine.rules_config import PPEOK_PENALTY_PI, SWEEP_BONUS_PI, TTADAK_PENALTY_PI
from engine.state import Event, EventType, GameState


def _pay_penalty(state: GameState, causer: int, pi_per_opponent: int) -> None:
    if pi_per_opponent <= 0:
        return
    causer_state = state.players[causer]
    for opp in state.opponents(causer):
        state.players[opp].bonus_pi_paid += pi_per_opponent
        causer_state.bonus_pi_received += pi_per_opponent


def _remove_from_field(state: GameState, month: int, card_ids: list[int]) -> None:
    pile = state.field.get(month, [])
    for cid in card_ids:
        pile.remove(cid)
    if pile:
        state.field[month] = pile
    else:
        state.field.pop(month, None)


def _check_sweep(state: GameState, player: int) -> None:
    if not state.field_cards():
        state.emit(Event(EventType.SWEEP, player, (), pi_penalty=SWEEP_BONUS_PI))
        _pay_penalty(state, player, SWEEP_BONUS_PI)


def finalize_capture(state: GameState, player: int, card_ids: list[int], event_type: EventType,
                       pi_per_opponent: int = 0) -> None:
    state.players[player].captured.extend(card_ids)
    state.emit(Event(event_type, player, tuple(card_ids), pi_penalty=pi_per_opponent))
    _pay_penalty(state, player, pi_per_opponent)
    _check_sweep(state, player)


def resolve_hand_play(state: GameState, player: int, card_id: int) -> None:
    """Removes card_id from the player's hand and resolves it against the field."""
    state.players[player].hand.discard(card_id)
    month = month_of(card_id)
    pile = list(state.field.get(month, []))

    if len(pile) == 0:
        state.field.setdefault(month, []).append(card_id)
        state.emit(Event(EventType.FIELD_ADD, player, (card_id,)))
    elif len(pile) == 1:
        # Deferred: don't capture yet, wait to see whether the draw creates a ppeok.
        state.field[month] = pile + [card_id]
        state.pending_pair = (card_id, pile[0])
    elif len(pile) == 2:
        _remove_from_field(state, month, pile)
        finalize_capture(state, player, pile + [card_id], EventType.CAPTURE)
        state.ttadak_watch_month = month
    else:  # len(pile) == 3: completing a locked ppeok/degenerate pile
        _remove_from_field(state, month, pile)
        finalize_capture(state, player, pile + [card_id], EventType.CAPTURE)


def resolve_draw(state: GameState, player: int, drawn_card_id: int) -> None:
    """Resolves the forced post-play deck draw, including any pending ppeok/ttadak check."""
    month = month_of(drawn_card_id)

    if state.pending_pair is not None:
        pending_month = month_of(state.pending_pair[0])
        if month == pending_month:
            # Ppeok: lock the trio (already sitting in state.field[month]) plus this draw.
            state.field[pending_month] = state.field[pending_month] + [drawn_card_id]
            causer = player
            state.emit(Event(EventType.PPEOK_LOCK, causer, tuple(state.field[pending_month]),
                              pi_penalty=PPEOK_PENALTY_PI))
            _pay_penalty(state, causer, PPEOK_PENALTY_PI)
            state.pending_pair = None
            return
        else:
            hand_card_id, field_card_id = state.pending_pair
            _remove_from_field(state, pending_month, [hand_card_id, field_card_id])
            finalize_capture(state, player, [hand_card_id, field_card_id], EventType.CAPTURE)
            state.pending_pair = None
            # fall through to resolve the draw itself below

    if state.ttadak_watch_month is not None and month == state.ttadak_watch_month:
        state.ttadak_watch_month = None
        finalize_capture(state, player, [drawn_card_id], EventType.TTADAK, pi_per_opponent=TTADAK_PENALTY_PI)
        return
    state.ttadak_watch_month = None

    pile = list(state.field.get(month, []))
    if len(pile) == 0:
        state.field.setdefault(month, []).append(drawn_card_id)
        state.emit(Event(EventType.FIELD_ADD, player, (drawn_card_id,)))
    elif len(pile) in (1, 2, 3):
        _remove_from_field(state, month, pile)
        finalize_capture(state, player, pile + [drawn_card_id], EventType.CAPTURE)
