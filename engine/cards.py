"""48-card Hwatu deck metadata. Card composition is pinned in RULES.md section 1 —
change the table there first if a rule variant changes the deck, not here.

Card ids are 0-47: id = (month - 1) * 4 + slot, slot in 0..3 per the per-month
ordering in _MONTH_SPECS below.
"""

from dataclasses import dataclass
from enum import Enum
import random


class Category(Enum):
    GWANG = "gwang"
    ANIMAL = "animal"
    RIBBON = "ribbon"
    JUNK = "junk"


@dataclass(frozen=True)
class Card:
    id: int
    month: int
    category: Category
    name: str
    is_godori: bool = False
    is_ssangpi: bool = False
    is_rain: bool = False
    ribbon_set: str | None = None  # "hongdan" | "chodan" | "cheongdan" | None


def _c(category, name, **flags):
    return (category, name, flags)


# Per-month card specs in the fixed slot order used to assign ids. Each entry is
# (category, name, flags) as produced by _c(). See RULES.md section 1 for sourcing.
_MONTH_SPECS: dict[int, list[tuple]] = {
    1: [_c(Category.GWANG, "crane_sun"), _c(Category.RIBBON, "hongdan_1", ribbon_set="hongdan"),
        _c(Category.JUNK, "pi_1a"), _c(Category.JUNK, "pi_1b")],
    2: [_c(Category.ANIMAL, "bush_warbler", is_godori=True), _c(Category.RIBBON, "hongdan_2", ribbon_set="hongdan"),
        _c(Category.JUNK, "pi_2a"), _c(Category.JUNK, "pi_2b")],
    3: [_c(Category.GWANG, "curtain"), _c(Category.RIBBON, "hongdan_3", ribbon_set="hongdan"),
        _c(Category.JUNK, "pi_3a"), _c(Category.JUNK, "pi_3b")],
    4: [_c(Category.ANIMAL, "cuckoo", is_godori=True), _c(Category.RIBBON, "chodan_4", ribbon_set="chodan"),
        _c(Category.JUNK, "pi_4a"), _c(Category.JUNK, "pi_4b")],
    5: [_c(Category.ANIMAL, "bridge"), _c(Category.RIBBON, "chodan_5", ribbon_set="chodan"),
        _c(Category.JUNK, "pi_5a"), _c(Category.JUNK, "pi_5b")],
    6: [_c(Category.ANIMAL, "butterflies"), _c(Category.RIBBON, "cheongdan_6", ribbon_set="cheongdan"),
        _c(Category.JUNK, "pi_6a"), _c(Category.JUNK, "pi_6b")],
    7: [_c(Category.ANIMAL, "boar"), _c(Category.RIBBON, "chodan_7", ribbon_set="chodan"),
        _c(Category.JUNK, "pi_7a"), _c(Category.JUNK, "pi_7b")],
    8: [_c(Category.GWANG, "full_moon"), _c(Category.ANIMAL, "geese", is_godori=True),
        _c(Category.JUNK, "pi_8a"), _c(Category.JUNK, "pi_8b")],
    9: [_c(Category.ANIMAL, "sake_cup"), _c(Category.RIBBON, "cheongdan_9", ribbon_set="cheongdan"),
        _c(Category.JUNK, "pi_9a"), _c(Category.JUNK, "pi_9b")],
    10: [_c(Category.ANIMAL, "deer"), _c(Category.RIBBON, "cheongdan_10", ribbon_set="cheongdan"),
         _c(Category.JUNK, "pi_10a"), _c(Category.JUNK, "pi_10b")],
    11: [_c(Category.GWANG, "phoenix"), _c(Category.JUNK, "pi_11a"), _c(Category.JUNK, "pi_11b"),
         _c(Category.JUNK, "ssangpi_11", is_ssangpi=True)],
    12: [_c(Category.GWANG, "rain_man", is_rain=True), _c(Category.ANIMAL, "swallow"),
         _c(Category.RIBBON, "rain_ribbon", ribbon_set=None),
         _c(Category.JUNK, "ssangpi_12", is_ssangpi=True)],
}


def _build_deck() -> tuple[Card, ...]:
    cards = []
    for month, specs in _MONTH_SPECS.items():
        for slot, (category, name, flags) in enumerate(specs):
            card_id = (month - 1) * 4 + slot
            cards.append(Card(id=card_id, month=month, category=category, name=name, **flags))
    cards.sort(key=lambda c: c.id)
    return tuple(cards)


CARDS: tuple[Card, ...] = _build_deck()
assert len(CARDS) == 48
assert sum(1 for c in CARDS if c.category is Category.GWANG) == 5
assert sum(1 for c in CARDS if c.category is Category.ANIMAL) == 9
assert sum(1 for c in CARDS if c.category is Category.RIBBON) == 10
assert sum(1 for c in CARDS if c.category is Category.JUNK) == 24
assert sum(1 for c in CARDS if c.is_ssangpi) == 2
assert sum(1 for c in CARDS if c.is_godori) == 3

GODORI_IDS: frozenset[int] = frozenset(c.id for c in CARDS if c.is_godori)
RIBBON_SETS: dict[str, frozenset[int]] = {
    name: frozenset(c.id for c in CARDS if c.ribbon_set == name)
    for name in ("hongdan", "chodan", "cheongdan")
}


def card(card_id: int) -> Card:
    return CARDS[card_id]


def month_of(card_id: int) -> int:
    return CARDS[card_id].month


def new_shuffled_deck(rng: random.Random | None = None) -> list[int]:
    rng = rng or random.Random()
    ids = list(range(48))
    rng.shuffle(ids)
    return ids


def pi_value(card_id: int) -> int:
    """Points a captured junk card contributes toward the pi-count score. 0 for non-junk cards."""
    c = CARDS[card_id]
    if c.category is not Category.JUNK:
        return 0
    return 2 if c.is_ssangpi else 1
