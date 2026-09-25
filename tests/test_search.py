import random

import numpy as np

from engine.engine import GoStopEngine
from rl.action_space import apply_action, legal_action_mask
from rl.baselines.heuristic_agent import heuristic_policy
from rl.search import SearchPolicy, determinize


def _mid_game_engine(seed: int = 3, plies: int = 6) -> GoStopEngine:
    engine = GoStopEngine(num_players=2, dealer=0, rng=random.Random(seed))
    for _ in range(plies):
        legal = np.flatnonzero(legal_action_mask(engine))
        apply_action(engine, int(heuristic_policy(engine, legal)))
    assert not engine.state.hand_over
    return engine


def _all_cards(state):
    cards = list(state.deck) + state.field_cards()
    for p in state.players:
        cards += list(p.hand) + list(p.captured)
    return cards


def test_determinized_world_conserves_all_48_cards():
    engine = _mid_game_engine()
    me = engine.state.turn
    world = determinize(engine, me, random.Random(0))
    assert sorted(_all_cards(world.state)) == list(range(48))


def test_determinize_keeps_everything_the_player_can_see():
    engine = _mid_game_engine()
    me = engine.state.turn
    opp = 1 - me
    world = determinize(engine, me, random.Random(0))
    assert world.state.players[me].hand == engine.state.players[me].hand
    assert world.state.players[me].captured == engine.state.players[me].captured
    assert world.state.players[opp].captured == engine.state.players[opp].captured
    assert world.state.field == engine.state.field
    assert len(world.state.players[opp].hand) == len(engine.state.players[opp].hand)
    assert len(world.state.deck) == len(engine.state.deck)


def test_determinize_does_not_mutate_the_real_game():
    engine = _mid_game_engine()
    me = engine.state.turn
    before_opp_hand = set(engine.state.players[1 - me].hand)
    before_deck = list(engine.state.deck)
    determinize(engine, me, random.Random(0))
    assert engine.state.players[1 - me].hand == before_opp_hand
    assert engine.state.deck == before_deck


def test_determinize_cannot_see_hidden_cards():
    # Two games identical in everything public, differing only in which hidden cards the opponent
    # holds vs. which are in the deck. Sampling must give the same worlds for both, or the search is
    # peeking at information it shouldn't have.
    a = _mid_game_engine()
    me = a.state.turn
    opp = 1 - me
    b = _mid_game_engine()
    hand = sorted(b.state.players[opp].hand)
    swap_out, swap_in = hand[0], b.state.deck[0]
    b.state.players[opp].hand.remove(swap_out)
    b.state.players[opp].hand.add(swap_in)
    b.state.deck[0] = swap_out
    assert b.state.players[opp].hand != a.state.players[opp].hand  # really differ in hidden info

    wa = determinize(a, me, random.Random(11))
    wb = determinize(b, me, random.Random(11))
    assert wa.state.players[opp].hand == wb.state.players[opp].hand
    assert wa.state.deck == wb.state.deck


def test_search_returns_a_legal_action_and_is_deterministic_per_seed():
    engine = _mid_game_engine()
    legal = np.flatnonzero(legal_action_mask(engine))
    first = SearchPolicy(determinizations=8, min_z=0.5, seed=5)(engine, legal)
    again = SearchPolicy(determinizations=8, min_z=0.5, seed=5)(engine, legal)
    assert first in legal
    assert first == again


def test_infinite_threshold_reduces_to_the_base_heuristic():
    engine = _mid_game_engine()
    legal = np.flatnonzero(legal_action_mask(engine))
    policy = SearchPolicy(determinizations=8, min_z=float("inf"))
    assert policy(engine, legal) == heuristic_policy(engine, legal)


def test_search_plays_a_full_game_with_only_legal_moves():
    engine = GoStopEngine(num_players=2, dealer=1, rng=random.Random(9))
    policy = SearchPolicy(determinizations=6, min_z=1.0, seed=1)
    steps = 0
    while not engine.state.hand_over:
        steps += 1
        assert steps < 200
        legal = np.flatnonzero(legal_action_mask(engine))
        action = policy(engine, legal)
        assert action in legal
        apply_action(engine, int(action))
    assert engine.state.result is not None


def test_nodes_restriction_leaves_other_decisions_to_the_base_policy():
    from engine.state import DecisionNode

    engine = _mid_game_engine()
    assert engine.state.pending_decision == DecisionNode.PLAY_CARD
    legal = np.flatnonzero(legal_action_mask(engine))
    policy = SearchPolicy(determinizations=8, min_z=0.0, seed=2, nodes="gostop")
    # a card-play decision with search restricted to go/stop: never searched
    assert policy(engine, legal) == heuristic_policy(engine, legal)
    assert policy.searched == 0
    searching = SearchPolicy(determinizations=8, min_z=0.0, seed=2, nodes="play")
    searching(engine, legal)
    assert searching.searched == 1


def test_served_search_bot_plays_a_full_game_legally():
    from api.bot_inference import load_search_bot_policy

    policy = load_search_bot_policy(determinizations=4)
    engine = GoStopEngine(num_players=2, dealer=0, rng=random.Random(21))
    steps = 0
    while not engine.state.hand_over:
        steps += 1
        assert steps < 200
        legal = np.flatnonzero(legal_action_mask(engine))
        action = policy(engine, legal)
        assert action in legal
        apply_action(engine, int(action))
