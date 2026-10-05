import random

from engine.cards import Category, card, month_of, new_shuffled_deck
from engine.rules_config import DEALING_TABLE, FIRST_DEALER_TIME_OF_DAY, REDEAL_ON_DEGENERATE_FIELD
from engine.state import GameState, HandResult, PlayerState

# Tiebreak rank within a month, lowest to highest (RULES.md #2a): bright > animal > ribbon > junk.
_CATEGORY_RANK = {Category.JUNK: 0, Category.RIBBON: 1, Category.ANIMAL: 2, Category.GWANG: 3}


def _is_degenerate_field(field_ids: list[int]) -> bool:
    counts: dict[int, int] = {}
    for cid in field_ids:
        m = month_of(cid)
        counts[m] = counts.get(m, 0) + 1
    return any(count >= 3 for count in counts.values())


def choose_first_dealer(num_players: int, rng: random.Random | None = None,
                         time_of_day: str = FIRST_DEALER_TIME_OF_DAY) -> int:
    """Each player draws one card from a freshly shuffled deck; see RULES.md #2a. A day game favors
    the latest month (ties broken by the higher-ranked card); a night game favors the earliest month
    (ties broken by the lower-ranked card). Returns the winning seat index."""
    if time_of_day not in ("day", "night"):
        raise ValueError(f"time_of_day must be 'day' or 'night', got {time_of_day!r}")
    rng = rng or random.Random()
    draws = new_shuffled_deck(rng)[:num_players]

    def key(card_id: int) -> tuple[int, int]:
        c = card(card_id)
        rank = _CATEGORY_RANK[c.category]
        return (c.month, rank) if time_of_day == "day" else (-c.month, -rank)

    return max(range(num_players), key=lambda seat: key(draws[seat]))


def choose_next_dealer(result: HandResult, previous_dealer: int) -> int:
    """Within one sitting, the winner of a hand deals the next one (RULES.md #2a); nagari is the
    pinned exception (RULES.md #11) -- the same dealer redeals. "Dealer" is only ever a turn-order
    label the engine tracks (see `GameState.dealer`, used solely to compute who plays first); no
    player performs an actual dealing action, so there's nothing else for this to drive."""
    if result.nagari or result.winner is None:
        return previous_dealer
    return result.winner


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
