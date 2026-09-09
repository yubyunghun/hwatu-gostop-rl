import random

from engine.cards import (
    CARDS, Category, GODORI_IDS, RIBBON_SETS, card, month_of, new_shuffled_deck, pi_value,
)


def test_deck_has_48_unique_cards():
    assert len(CARDS) == 48
    assert len({c.id for c in CARDS}) == 48
    assert {c.id for c in CARDS} == set(range(48))


def test_each_month_has_exactly_four_cards():
    for month in range(1, 13):
        assert sum(1 for c in CARDS if c.month == month) == 4


def test_category_totals_match_rules_md():
    counts = {cat: sum(1 for c in CARDS if c.category is cat) for cat in Category}
    assert counts[Category.GWANG] == 5
    assert counts[Category.ANIMAL] == 9
    assert counts[Category.RIBBON] == 10
    assert counts[Category.JUNK] == 24


def test_ssangpi_cards_are_months_11_and_12():
    ssangpi_months = {card(c.id).month for c in CARDS if c.is_ssangpi}
    assert ssangpi_months == {11, 12}
    assert sum(1 for c in CARDS if c.is_ssangpi) == 2


def test_godori_is_feb_apr_aug_animals():
    godori_months = sorted(month_of(cid) for cid in GODORI_IDS)
    assert godori_months == [2, 4, 8]
    for cid in GODORI_IDS:
        assert card(cid).category is Category.ANIMAL


def test_ribbon_sets_partition_correctly():
    assert sorted(month_of(cid) for cid in RIBBON_SETS["hongdan"]) == [1, 2, 3]
    assert sorted(month_of(cid) for cid in RIBBON_SETS["chodan"]) == [4, 5, 7]
    assert sorted(month_of(cid) for cid in RIBBON_SETS["cheongdan"]) == [6, 9, 10]
    # December's ribbon exists but belongs to no color set.
    december_ribbon = [c for c in CARDS if c.month == 12 and c.category is Category.RIBBON]
    assert len(december_ribbon) == 1
    assert december_ribbon[0].ribbon_set is None


def test_months_8_and_11_have_no_ribbon():
    for month in (8, 11):
        assert not any(c.month == month and c.category is Category.RIBBON for c in CARDS)


def test_pi_value_counts_ssangpi_as_two():
    ssangpi_id = next(c.id for c in CARDS if c.is_ssangpi)
    plain_pi_id = next(c.id for c in CARDS if c.category is Category.JUNK and not c.is_ssangpi)
    non_junk_id = next(c.id for c in CARDS if c.category is not Category.JUNK)
    assert pi_value(ssangpi_id) == 2
    assert pi_value(plain_pi_id) == 1
    assert pi_value(non_junk_id) == 0


def test_new_shuffled_deck_is_a_permutation_of_48():
    deck = new_shuffled_deck(random.Random(42))
    assert sorted(deck) == list(range(48))
