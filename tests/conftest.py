from engine.cards import month_of
from engine.state import DecisionNode, GameState, PlayerState


def make_state(num_players=2, hands=None, field_ids=None, deck=None, turn=0, dealer=0):
    """Builds a GameState with explicit card placements for isolated rule testing.
    Any card ids not mentioned anywhere are simply left unaccounted for -- fine for
    unit tests that only care about a specific interaction, not full-deck bookkeeping."""
    hands = hands or [set() for _ in range(num_players)]
    field_ids = field_ids or []
    deck = list(deck or [])

    field: dict[int, list[int]] = {}
    for cid in field_ids:
        field.setdefault(month_of(cid), []).append(cid)

    players = [PlayerState(hand=set(hands[i])) for i in range(num_players)]
    return GameState(
        num_players=num_players,
        deck=deck,
        field=field,
        players=players,
        turn=turn,
        dealer=dealer,
        pending_decision=DecisionNode.PLAY_CARD,
    )
