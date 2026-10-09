"""Capture resolution for a hand-play followed by its forced deck draw.

See RULES.md sections 4-5 for the mechanics this encodes. A hand-play matching exactly 1 field
card is *not* finalized immediately -- it is held as `state.pending_pair` until the following draw
is known, because if that draw is also the same month the whole trio locks as a ppeok pile instead
of being captured (section 5).

A played/drawn card matching exactly 2 field cards is *also* not finalized immediately and does not
auto-capture both: per RULES.md #4 (pagat), the player chooses which of the two to pair with --
`state.pending_capture_choice` holds the card and both candidates until a CAPTURE_CHOICE decision
resolves it (`resolve_capture_choice`), at which point it becomes an ordinary `pending_pair` exactly
like the 1-match case, except `state.field[month]` already has 3 cards in it (the played/drawn card
plus both original field cards) instead of 2 -- that's how `resolve_draw` tells the two cases
apart: if the next card to touch that month also matches, a 2-card pending pair locks as a 3-card
ppeok, but a 3-card one captures all 4 immediately (there's no partial pile left to resolve later).
This can happen on either half of a turn -- the hand-play or the forced draw that follows it -- so
GoStopEngine pauses turn resolution at whichever point it comes up
(`state.capture_choice_after_draw` records which, for where to resume once it's answered).
"""

from engine.cards import Category, card, month_of
from engine.rules_config import PPEOK_PENALTY_PI, SWEEP_BONUS_PI
from engine.state import DecisionNode, Event, EventType, GameState


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
    if card(card_id).category is Category.BONUS:
        # A bonus card is never a legal PLAY_CARD choice -- GoStopEngine._resolve_bonus_cards_in_hand
        # always resolves it out of a hand before PLAY_CARD is ever offered (RULES.md #12). Reaching
        # here means that invariant broke; fail loudly rather than silently filing it under
        # field[None], which month_of's None would otherwise do.
        raise ValueError(f"bonus card {card_id} cannot be played as a field move")
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
        # Deferred differently: place the card (now 3 of this month sit together) and ask which of
        # the two original field cards it pairs with -- see resolve_capture_choice.
        state.field[month] = pile + [card_id]
        state.pending_capture_choice = (card_id, (pile[0], pile[1]))
        state.pending_decision = DecisionNode.CAPTURE_CHOICE
        state.capture_choice_after_draw = False
    else:  # len(pile) == 3: completing a locked ppeok/degenerate pile
        _remove_from_field(state, month, pile)
        finalize_capture(state, player, pile + [card_id], EventType.CAPTURE)


def resolve_capture_choice(state: GameState, player: int, chosen_field_card_id: int) -> None:
    """Resolves a pending CAPTURE_CHOICE: pairs the played/drawn card (set aside in
    pending_capture_choice) with the chosen field card. The unchosen one is left exactly where it
    already is in state.field[month] -- RULES.md #4, quoting pagat: "you can choose on which one you
    will place your played card"; the rules don't say the other one goes anywhere, so it doesn't.

    What happens to the resulting pair differs by which half of the turn this choice came from:
    - From the hand-play (capture_choice_after_draw=False): defer it as an ordinary pending_pair,
      same as the 1-match case, because the forced draw that's about to happen still needs checking
      for a ppeok or a 4-card sweep.
    - From the forced draw (capture_choice_after_draw=True): there's no further draw left this turn
      to wait on, so the pair captures immediately."""
    played_card_id, candidates = state.pending_capture_choice
    if chosen_field_card_id not in candidates:
        raise ValueError(f"{chosen_field_card_id} is not a legal capture-choice target "
                          f"(candidates were {candidates})")
    state.pending_capture_choice = None
    if state.capture_choice_after_draw:
        _remove_from_field(state, month_of(played_card_id), [played_card_id, chosen_field_card_id])
        finalize_capture(state, player, [played_card_id, chosen_field_card_id], EventType.CAPTURE)
    else:
        state.pending_pair = (played_card_id, chosen_field_card_id)


def _resolve_bonus_draw(state: GameState, player: int, drawn_card_id: int) -> None:
    """A bonus card turned up by the forced post-play draw is collected outright (RULES.md #12). It
    has no month, so it can never be the card that turns a pending pair into a ppeok -- that pair, if
    any, resolves as an ordinary non-matching draw first, same as it would for any other card."""
    if state.pending_pair is not None:
        hand_card_id, field_card_id = state.pending_pair
        _remove_from_field(state, month_of(hand_card_id), [hand_card_id, field_card_id])
        finalize_capture(state, player, [hand_card_id, field_card_id], EventType.CAPTURE)
        state.pending_pair = None
    state.players[player].captured.append(drawn_card_id)
    state.emit(Event(EventType.BONUS_CARD, player, (drawn_card_id,)))


def resolve_draw(state: GameState, player: int, drawn_card_id: int) -> None:
    """Resolves the forced post-play deck draw, including any pending ppeok check."""
    if card(drawn_card_id).category is Category.BONUS:
        _resolve_bonus_draw(state, player, drawn_card_id)
        return

    month = month_of(drawn_card_id)

    if state.pending_pair is not None:
        pending_month = month_of(state.pending_pair[0])
        if month == pending_month:
            already_there = state.field[pending_month]
            if len(already_there) >= 3:
                # Came from a CAPTURE_CHOICE (RULES.md #4): all 3 of this month plus the draw makes
                # 4 -- a straight capture, not a ppeok lock (pagat: "you capture all four cards of
                # this month"). The card left unchosen earlier gets swept up here after all.
                captured_ids = list(already_there) + [drawn_card_id]
                _remove_from_field(state, pending_month, list(already_there))
                finalize_capture(state, player, captured_ids, EventType.CAPTURE)
            else:
                # Ppeok: lock the trio (already sitting in state.field[month]) plus this draw.
                state.field[pending_month] = already_there + [drawn_card_id]
                state.emit(Event(EventType.PPEOK_LOCK, player, tuple(state.field[pending_month]),
                                  pi_penalty=PPEOK_PENALTY_PI))
                _pay_penalty(state, player, PPEOK_PENALTY_PI)
            state.pending_pair = None
            return
        else:
            hand_card_id, field_card_id = state.pending_pair
            _remove_from_field(state, pending_month, [hand_card_id, field_card_id])
            finalize_capture(state, player, [hand_card_id, field_card_id], EventType.CAPTURE)
            state.pending_pair = None
            # fall through to resolve the draw itself below

    pile = list(state.field.get(month, []))
    if len(pile) == 0:
        state.field.setdefault(month, []).append(drawn_card_id)
        state.emit(Event(EventType.FIELD_ADD, player, (drawn_card_id,)))
    elif len(pile) == 2:
        # Same choice as a hand-play matching 2 (RULES.md #4) -- the drawn card is just as much a
        # single card being placed against the layout as a played one is.
        state.field[month] = pile + [drawn_card_id]
        state.pending_capture_choice = (drawn_card_id, (pile[0], pile[1]))
        state.pending_decision = DecisionNode.CAPTURE_CHOICE
        state.capture_choice_after_draw = True
    elif len(pile) in (1, 3):
        _remove_from_field(state, month, pile)
        finalize_capture(state, player, pile + [drawn_card_id], EventType.CAPTURE)
