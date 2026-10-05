import random

from engine.cards import Category, card, month_of, new_shuffled_deck
from engine.rules_config import DEALING_TABLE, FIRST_DEALER_TIME_OF_DAY, REDEAL_ON_DEGENERATE_FIELD
from engine.state import GameState, HandResult, PlayerState

# Tiebreak rank within a month, lowest to highest (RULES.md #2a): bright > animal > ribbon > junk.
_CATEGORY_RANK = {Category.JUNK: 0, Category.RIBBON: 1, Category.ANIMAL: 2, Category.GWANG: 3}


def _is_degenerate_field(field_ids: list[int]) -> bool:
    counts: dict[int, int] = {}
    for cid in field_ids:
        if card(cid).category is Category.BONUS:
            continue  # has no month, can't be part of an unresolvable same-month pile
        m = month_of(cid)
        counts[m] = counts.get(m, 0) + 1
    return any(count >= 3 for count in counts.values())


def draw_blind_replacement(pile: list[int], rng: random.Random) -> int:
    """Removes and returns one card from `pile` without looking at any of them first -- used for a
    bonus card's hand replacement (RULES.md #12: "you can choose any of the cards in the deck
    without seeing it"), which is a free pick of position but not of identity, so it's equivalent to
    a uniform-random draw. Mutates `pile` in place."""
    return pile.pop(rng.randrange(len(pile)))


def _resolve_initial_bonus_cards(field_ids: list[int], draw_pile: list[int], dealer_captured: list[int],
                                   ) -> list[int]:
    """A bonus card dealt face-up at the initial deal is swapped out immediately: the dealer banks it
    and the *top* card of the stock is turned up in its place (RULES.md #12, quoting Wikipedia: "the
    dealer collects the bonus card and turns the top card of the draw pile face-up"). Repeats if that
    replacement is itself a bonus card. Returns the field ids with every bonus card resolved out."""
    resolved: list[int] = []
    pending = list(field_ids)
    while pending:
        cid = pending.pop(0)
        if card(cid).category is not Category.BONUS:
            resolved.append(cid)
            continue
        dealer_captured.append(cid)
        if draw_pile:
            pending.append(draw_pile.pop(0))
    return resolved


def choose_first_dealer(num_players: int, rng: random.Random | None = None,
                         time_of_day: str = FIRST_DEALER_TIME_OF_DAY) -> int:
    """Each player draws one card from a freshly shuffled deck; see RULES.md #2a. A day game favors
    the latest month (ties broken by the higher-ranked card); a night game favors the earliest month
    (ties broken by the lower-ranked card). Returns the winning seat index.

    A bonus card (RULES.md #12), if any are in play, is never one of the draws: it has no month or
    category rank to compare by, and nothing in any source describes using one for this -- the
    natural reading is that only the real 48 ever take part."""
    if time_of_day not in ("day", "night"):
        raise ValueError(f"time_of_day must be 'day' or 'night', got {time_of_day!r}")
    rng = rng or random.Random()
    shuffled = [cid for cid in new_shuffled_deck(rng) if card(cid).category is not Category.BONUS]
    draws = shuffled[:num_players]

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
        # Everything left over, not a fixed `sizes["deck"]` slice -- bonus cards (if any) only ever
        # enlarge the undealt stock, never the hand or field sizes pinned in RULES.md #2.
        draw_pile = deck[cursor:]

        if not (REDEAL_ON_DEGENERATE_FIELD and _is_degenerate_field(field_ids)):
            break

    players = [PlayerState(hand=hands[i]) for i in range(num_players)]
    field_ids = _resolve_initial_bonus_cards(field_ids, draw_pile, players[dealer].captured)

    field: dict[int, list[int]] = {}
    for cid in field_ids:
        field.setdefault(month_of(cid), []).append(cid)

    first_turn = (dealer + 1) % num_players
    return GameState(
        num_players=num_players,
        deck=draw_pile,
        field=field,
        players=players,
        turn=first_turn,
        dealer=dealer,
    )
