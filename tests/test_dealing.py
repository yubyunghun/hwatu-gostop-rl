import random

from engine.cards import month_of
from engine.dealing import deal_new_hand
from engine.state import DecisionNode


def test_two_player_deal_sizes():
    state = deal_new_hand(2, dealer=0, rng=random.Random(1))
    assert len(state.players) == 2
    assert all(len(p.hand) == 10 for p in state.players)
    assert sum(len(pile) for pile in state.field.values()) == 6
    assert len(state.deck) == 22


def test_three_player_deal_sizes():
    state = deal_new_hand(3, dealer=0, rng=random.Random(1))
    assert len(state.players) == 3
    assert all(len(p.hand) == 7 for p in state.players)
    assert sum(len(pile) for pile in state.field.values()) == 8
    assert len(state.deck) == 19


def test_deal_uses_every_card_exactly_once():
    state = deal_new_hand(2, dealer=0, rng=random.Random(7))
    all_ids: list[int] = []
    for p in state.players:
        all_ids.extend(p.hand)
    all_ids.extend(state.field_cards())
    all_ids.extend(state.deck)
    assert sorted(all_ids) == list(range(48))


def test_first_turn_is_player_after_dealer():
    state = deal_new_hand(2, dealer=0, rng=random.Random(1))
    assert state.turn == 1
    state = deal_new_hand(3, dealer=2, rng=random.Random(1))
    assert state.turn == 0


def test_deal_never_produces_degenerate_field():
    for seed in range(200):
        state = deal_new_hand(2, dealer=0, rng=random.Random(seed))
        counts: dict[int, int] = {}
        for cid in state.field_cards():
            counts[month_of(cid)] = counts.get(month_of(cid), 0) + 1
        assert all(count < 3 for count in counts.values())


def test_initial_pending_decision_is_play_card():
    state = deal_new_hand(2, dealer=0, rng=random.Random(1))
    assert state.pending_decision == DecisionNode.PLAY_CARD


def test_choose_first_dealer_returns_a_valid_seat_and_is_deterministic_per_seed():
    from engine.dealing import choose_first_dealer

    a = choose_first_dealer(2, random.Random(5))
    b = choose_first_dealer(2, random.Random(5))
    assert a == b
    assert a in (0, 1)


def test_choose_first_dealer_day_favors_latest_month_night_favors_earliest():
    from unittest.mock import patch

    from engine.dealing import choose_first_dealer

    # Rig the "deal": seat 0 draws January gwang (month 1), seat 1 draws December ssangpi (month 12).
    with patch("engine.dealing.new_shuffled_deck", return_value=[0, 47, 1, 2]):
        assert choose_first_dealer(2, random.Random(0), time_of_day="day") == 1
        assert choose_first_dealer(2, random.Random(0), time_of_day="night") == 0


def test_choose_first_dealer_tiebreak_uses_category_rank():
    from unittest.mock import patch

    from engine.dealing import choose_first_dealer

    # Same month (January: id 0 = gwang, id 2 = junk). Day favors the higher rank, night the lower.
    with patch("engine.dealing.new_shuffled_deck", return_value=[2, 0]):
        assert choose_first_dealer(2, random.Random(0), time_of_day="day") == 1
        assert choose_first_dealer(2, random.Random(0), time_of_day="night") == 0


def test_choose_first_dealer_rejects_bad_time_of_day():
    import pytest

    from engine.dealing import choose_first_dealer

    with pytest.raises(ValueError):
        choose_first_dealer(2, random.Random(0), time_of_day="noon")
