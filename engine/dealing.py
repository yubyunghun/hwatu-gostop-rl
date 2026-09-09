import random

from engine.cards import month_of, new_shuffled_deck
from engine.rules_config import DEALING_TABLE, REDEAL_ON_DEGENERATE_FIELD
from engine.state import GameState, PlayerState


def _is_degenerate_field(field_ids: list[int]) -> bool:
    counts: dict[int, int] = {}
    for cid in field_ids:
        m = month_of(cid)
        counts[m] = counts.get(m, 0) + 1
    return any(count >= 3 for count in counts.values())


def deal_new_hand(num_players: int, dealer: int, rng: random.Random | None = None) -> GameState:
    if num_players not in DEALING_TABLE:
        raise ValueError(f"no dealing table entry for {num_players} players")
    rng = rng or random.Random()
    sizes = DEALING_TABLE[num_players]

    while True:
        deck = new_shuffled_deck(rng)
        hands: list[set[int]] = []
        cursor = 0
        for _ in range(num_players):
            hands.append(set(deck[cursor:cursor + sizes["hand"]]))
            cursor += sizes["hand"]
        field_ids = deck[cursor:cursor + sizes["field"]]
        cursor += sizes["field"]
        draw_pile = deck[cursor:cursor + sizes["deck"]]

        if not (REDEAL_ON_DEGENERATE_FIELD and _is_degenerate_field(field_ids)):
            break

    field: dict[int, list[int]] = {}
    for cid in field_ids:
        field.setdefault(month_of(cid), []).append(cid)

    players = [PlayerState(hand=hands[i]) for i in range(num_players)]
    first_turn = (dealer + 1) % num_players
    return GameState(
        num_players=num_players,
        deck=draw_pile,
        field=field,
        players=players,
        turn=first_turn,
        dealer=dealer,
    )
