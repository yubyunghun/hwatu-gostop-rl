"""Final-hand scoring. See RULES.md sections 8-9. `score_player` computes a player's
raw category score (gwang/animal/ribbon/godori/pi) from their captured pile alone;
`settle` turns a pair of raw scores plus go-counts into final payments, applying
gwang-bak/pi-bak/meong-bak and the go/stop multiplier progression."""

from dataclasses import dataclass

from engine.cards import Category, GODORI_IDS, RIBBON_SETS, card, pi_value
from engine.rules_config import (
    ANIMAL_SCORE_THRESHOLD, GO_BONUS_POINTS, GO_MULTIPLIER_START, GOBAK_ENABLED, GOBAK_MULTIPLIER,
    GODORI_BONUS, GWANG_BAK_THRESHOLD, GWANG_SCORE_TABLE, MEONG_BAK_THRESHOLD, PI_BAK_THRESHOLD,
    PI_SCORE_THRESHOLD, RAIN_GWANG_PENALTY, RIBBON_SCORE_THRESHOLD, RIBBON_SET_BONUS,
)


@dataclass
class RawScore:
    gwang: int
    animal: int
    ribbon: int
    pi: int
    total: int
    gwang_count: int
    animal_count: int
    pi_count: int


def _gwang_score(gwang_ids: list[int]) -> int:
    count = len(gwang_ids)
    if count not in GWANG_SCORE_TABLE:
        return 0
    score = GWANG_SCORE_TABLE[count]
    if count == 3 and any(card(cid).is_rain for cid in gwang_ids):
        score -= RAIN_GWANG_PENALTY
    return score


def _animal_score(animal_ids: list[int]) -> int:
    count = len(animal_ids)
    score = 0
    if count >= ANIMAL_SCORE_THRESHOLD:
        score += 1 + (count - ANIMAL_SCORE_THRESHOLD)
    if GODORI_IDS.issubset(animal_ids):
        score += GODORI_BONUS
    return score


def _ribbon_score(ribbon_ids: list[int]) -> int:
    count = len(ribbon_ids)
    score = 0
    if count >= RIBBON_SCORE_THRESHOLD:
        score += 1 + (count - RIBBON_SCORE_THRESHOLD)
    held = set(ribbon_ids)
    for members in RIBBON_SETS.values():
        if members.issubset(held):
            score += RIBBON_SET_BONUS
    return score


def score_player(captured: list[int], bonus_pi_received: int = 0, bonus_pi_paid: int = 0) -> RawScore:
    by_category: dict[Category, list[int]] = {c: [] for c in Category}
    for cid in captured:
        by_category[card(cid).category].append(cid)

    gwang = _gwang_score(by_category[Category.GWANG])
    animal = _animal_score(by_category[Category.ANIMAL])
    ribbon = _ribbon_score(by_category[Category.RIBBON])
    pi_raw = sum(pi_value(cid) for cid in by_category[Category.JUNK])
    pi_count = pi_raw + bonus_pi_received - bonus_pi_paid
    pi = 0
    if pi_count >= PI_SCORE_THRESHOLD:
        pi = 1 + (pi_count - PI_SCORE_THRESHOLD)

    return RawScore(
        gwang=gwang, animal=animal, ribbon=ribbon, pi=pi,
        total=gwang + animal + ribbon + pi,
        gwang_count=len(by_category[Category.GWANG]),
        animal_count=len(by_category[Category.ANIMAL]),
        pi_count=pi_count,
    )


def go_multiplier(go_count: int) -> int:
    if go_count < GO_MULTIPLIER_START:
        return 1
    return 2 ** (go_count - (GO_MULTIPLIER_START - 1))


@dataclass
class Settlement:
    winner: int
    base_score: int
    go_bonus: int
    multiplier: int
    gwang_bak: bool
    pi_bak: bool
    meong_bak: bool
    final_score: int


def settle(winner: int, winner_raw: RawScore, loser_raw: RawScore, winner_go_count: int,
           loser_called_go: bool) -> Settlement:
    base = winner_raw.total
    go_bonus = winner_go_count * GO_BONUS_POINTS
    score_with_go = base + go_bonus

    gwang_bak = winner_raw.gwang > 0 and loser_raw.gwang_count <= GWANG_BAK_THRESHOLD
    pi_bak = winner_raw.pi > 0 and loser_raw.pi_count < PI_BAK_THRESHOLD
    meong_bak = winner_raw.animal_count >= MEONG_BAK_THRESHOLD

    multiplier = go_multiplier(winner_go_count)
    if gwang_bak:
        multiplier *= 2
    if pi_bak:
        multiplier *= 2
    if meong_bak:
        multiplier *= 2
    if GOBAK_ENABLED and loser_called_go:
        multiplier *= GOBAK_MULTIPLIER

    return Settlement(
        winner=winner, base_score=base, go_bonus=go_bonus, multiplier=multiplier,
        gwang_bak=gwang_bak, pi_bak=pi_bak, meong_bak=meong_bak,
        final_score=score_with_go * multiplier,
    )
