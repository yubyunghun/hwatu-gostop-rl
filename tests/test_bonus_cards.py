"""Bonus cards (RULES.md #12): off by default (`NUM_BONUS_CARDS = 0`, exercised by every other test
file unmodified), so these tests turn them on locally by patching `engine.cards.CARDS` to a deck that
includes some, rather than touching the process-wide config. `card()`/`month_of()`/`pi_value()`/
`new_shuffled_deck()` all read `CARDS` as a module global at call time (not a value captured at
import time), so this patch is picked up correctly by every module that calls them, with no reload
needed -- see `engine/cards.py`'s `_build_deck`.
"""

import random
from contextlib import ExitStack
from unittest.mock import patch

from engine.cards import Category, _build_deck, card, pi_value
from engine.capture import resolve_draw
from engine.dealing import _resolve_initial_bonus_cards, deal_new_hand, draw_blind_replacement
from engine.engine import GoStopEngine
from engine.scoring import score_player
from engine.state import DecisionNode, EventType, GameState, PlayerState

NUM_BONUS = 3
_BONUS_CARDS = _build_deck(NUM_BONUS)  # 48 standard + 3 bonus (ids 48, 49, 50)
_BONUS_IDS = [48, 49, 50]


def _with_bonus_cards():
    """A context manager patching engine.cards.CARDS for the duration of a `with` block. Enough for
    everything in engine/ -- card()/month_of()/pi_value()/new_shuffled_deck() all read CARDS as a
    module global at call time, not a value captured at import time (see engine/cards.py)."""
    import engine.cards as cards_module
    return patch.object(cards_module, "CARDS", _BONUS_CARDS)


def _with_bonus_cards_and_rl_resized():
    """Like `_with_bonus_cards`, but also patches every rl/ module constant that's baked in from
    engine.cards.NUM_CARDS at *import* time (NUM_CARDS, ACTION_SIZE, SKIP, GO, STOP in
    rl/action_space.py; NUM_CARDS in rl/search.py) -- those are plain ints copied in once, not live
    lookups, so a CARDS-only patch doesn't reach them. This reproduces exactly what a process started
    with NUM_BONUS_CARDS = 3 would have computed, for testing rl/action_space.py and rl/search.py's
    dynamic sizing without the fragility of reloading modules. Also covers
    rl/baselines/heuristic_agent.py's GO/STOP, which it imports by value at its own module load
    ("from rl.action_space import GO, STOP") -- a real server process started fresh with
    HWATU_NUM_BONUS_CARDS set has no staleness problem here since import order makes every module
    compute its constants from the correctly-configured registry the first and only time; this test
    helper just has to patch each copy explicitly since it's simulating that after the fact."""
    import engine.cards as cards_module
    import rl.action_space as action_space_module
    import rl.baselines.heuristic_agent as heuristic_agent_module
    import rl.search as search_module
    n = len(_BONUS_CARDS)
    stack = ExitStack()
    stack.enter_context(patch.object(cards_module, "CARDS", _BONUS_CARDS))
    stack.enter_context(patch.object(cards_module, "NUM_CARDS", n))
    stack.enter_context(patch.object(action_space_module, "NUM_CARDS", n))
    stack.enter_context(patch.object(action_space_module, "SKIP", n))
    stack.enter_context(patch.object(action_space_module, "GO", n + 1))
    stack.enter_context(patch.object(action_space_module, "STOP", n + 2))
    stack.enter_context(patch.object(action_space_module, "ACTION_SIZE", n + 3))
    stack.enter_context(patch.object(search_module, "NUM_CARDS", n))
    stack.enter_context(patch.object(heuristic_agent_module, "GO", n + 1))
    stack.enter_context(patch.object(heuristic_agent_module, "STOP", n + 2))
    return stack


def test_build_deck_adds_monthless_bonus_cards_worth_the_pinned_pi_value():
    assert len(_BONUS_CARDS) == 48 + NUM_BONUS
    bonus = [c for c in _BONUS_CARDS if c.category is Category.BONUS]
    assert [c.id for c in bonus] == _BONUS_IDS
    assert all(c.month is None for c in bonus)
    with _with_bonus_cards():
        assert all(pi_value(cid) == 2 for cid in _BONUS_IDS)  # BONUS_CARD_PI_VALUE, same as a ssangpi


def test_build_deck_with_zero_bonus_cards_is_the_plain_48():
    assert _build_deck(0) == _build_deck(0)
    assert len(_build_deck(0)) == 48
    assert all(c.category is not Category.BONUS for c in _build_deck(0))


# -- initial deal: a bonus card on the table at the deal is swapped out immediately --------------

def test_resolve_initial_bonus_cards_captures_it_for_the_dealer_and_draws_the_top_replacement():
    with _with_bonus_cards():
        dealer_captured: list[int] = []
        draw_pile = [10, 11, 12]
        resolved = _resolve_initial_bonus_cards([48, 1, 2, 3, 4, 5], draw_pile, dealer_captured)

        assert 48 not in resolved
        assert dealer_captured == [48]
        assert resolved == [1, 2, 3, 4, 5, 10]  # top of the stock (10), per Wikipedia's wording
        assert draw_pile == [11, 12]


def test_resolve_initial_bonus_cards_cascades_if_the_replacement_is_itself_a_bonus_card():
    with _with_bonus_cards():
        dealer_captured: list[int] = []
        draw_pile = [50, 10, 11]
        resolved = _resolve_initial_bonus_cards([48, 49, 1, 2, 3, 4], draw_pile, dealer_captured)

        assert set(dealer_captured) == {48, 49, 50}  # the original two, plus the bonus replacement
        assert sorted(resolved) == [1, 2, 3, 4, 10, 11]
        assert draw_pile == []


def test_resolve_initial_bonus_cards_is_a_no_op_with_no_bonus_cards_present():
    with _with_bonus_cards():
        dealer_captured: list[int] = []
        draw_pile = [10, 11]
        resolved = _resolve_initial_bonus_cards([1, 2, 3, 4, 5, 6], draw_pile, dealer_captured)
        assert resolved == [1, 2, 3, 4, 5, 6]
        assert dealer_captured == []
        assert draw_pile == [10, 11]


def test_deal_new_hand_conserves_all_cards_including_bonus_ones():
    with _with_bonus_cards():
        for seed in range(30):
            state = deal_new_hand(2, dealer=0, rng=random.Random(seed))
            all_ids: list[int] = []
            for p in state.players:
                all_ids.extend(p.hand)
                all_ids.extend(p.captured)
            all_ids.extend(state.field_cards())
            all_ids.extend(state.deck)
            assert sorted(all_ids) == list(range(51))
            # A bonus card is never left sitting in the field -- it's resolved at deal time.
            assert all(card(cid).category is not Category.BONUS for cid in state.field_cards())
            # Hand/field sizes are exactly the pinned ones regardless of bonus cards (RULES.md #2);
            # only the undealt stock grows.
            assert all(len(p.hand) == 10 for p in state.players)
            assert sum(len(pile) for pile in state.field.values()) == 6


def test_deal_new_hand_scores_a_dealer_captured_bonus_card_toward_their_total():
    with _with_bonus_cards():
        # Keep rolling seeds until one actually deals a bonus card onto the table, so the dealer's
        # captured pile is nonempty straight out of the deal.
        for seed in range(200):
            state = deal_new_hand(2, dealer=0, rng=random.Random(seed))
            if state.players[0].captured:
                assert all(card(cid).category is Category.BONUS for cid in state.players[0].captured)
                raw = score_player(state.players[0].captured)
                assert raw.pi_count == 2 * len(state.players[0].captured)
                return
        raise AssertionError("no seed in range produced an initial-deal bonus card in 200 tries")


# -- drawn from the stock mid-turn: auto-collected, pending pair resolves as a non-match ----------

def test_resolve_draw_collects_a_bonus_card_outright():
    with _with_bonus_cards():
        state = GameState(num_players=2, deck=[], field={}, players=[PlayerState(), PlayerState()],
                            turn=0, dealer=0)
        resolve_draw(state, player=0, drawn_card_id=48)
        assert state.players[0].captured == [48]
        assert state.events[-1].type is EventType.BONUS_CARD
        assert state.pending_pair is None


def test_resolve_draw_of_a_bonus_card_resolves_a_pending_pair_as_a_non_match_first():
    with _with_bonus_cards():
        # Matches resolve_hand_play's len(pile) == 1 branch: the hand card (0) is already sitting in
        # the field alongside the one it matched (2), both pending until the following draw is known.
        state = GameState(num_players=2, deck=[], field={1: [0, 2]}, players=[PlayerState(), PlayerState()],
                            turn=0, dealer=0)
        state.pending_pair = (0, 2)  # hand card 0 (January) matched field card 2 (January)
        state.ttadak_watch_month = 1

        resolve_draw(state, player=0, drawn_card_id=48)

        assert state.pending_pair is None
        assert state.ttadak_watch_month is None
        assert sorted(state.players[0].captured) == [0, 2, 48]  # the pair, plus the bonus card
        assert state.field == {}


# -- dealt into a hand: banked at the start of the holder's turn for a blind replacement ----------

def test_engine_banks_a_hand_held_bonus_card_at_the_start_of_the_turn():
    with _with_bonus_cards():
        engine = GoStopEngine(num_players=2, dealer=0, rng=random.Random(1))
        player = engine.state.turn
        engine.state.players[player].hand.add(48)
        # A real, valid, non-bonus card id (the loop re-scans the whole hand afterwards looking for a
        # cascading bonus replacement -- see the next test -- so this has to be a real card() lookup).
        engine.state.deck = [1]

        engine._resolve_bonus_cards_in_hand(player)

        assert 48 not in engine.state.players[player].hand
        assert 48 in engine.state.players[player].captured
        assert 1 in engine.state.players[player].hand  # replacement drawn blind from the deck
        assert engine.state.deck == []


def test_engine_resolves_a_cascading_bonus_card_replacement():
    """The blind replacement itself can be another bonus card; that one needs resolving too, in the
    same turn, not left sitting in the hand for a future PLAY_CARD decision to trip over."""
    with _with_bonus_cards():
        engine = GoStopEngine(num_players=2, dealer=0, rng=random.Random(1))
        player = engine.state.turn
        engine.state.players[player].hand.add(48)
        engine.state.deck = [49, 1]  # the first replacement (49) is itself a bonus card

        engine._resolve_bonus_cards_in_hand(player)

        assert engine.state.players[player].hand.isdisjoint({48, 49})
        assert {48, 49}.issubset(set(engine.state.players[player].captured))
        assert 1 in engine.state.players[player].hand
        assert engine.state.deck == []


def test_engine_never_offers_a_bonus_card_as_a_play_card_option():
    with _with_bonus_cards():
        from rl.action_space import legal_action_mask

        engine = GoStopEngine(num_players=2, dealer=0, rng=random.Random(1))
        # Only the player about to act is guaranteed resolved -- the other player's bonus cards (if
        # any) stay in their hand, unresolved, until their own turn comes up (RULES.md #12).
        assert all(card(cid).category is not Category.BONUS
                   for cid in engine.state.players[engine.state.turn].hand)
        if engine.state.pending_decision == DecisionNode.PLAY_CARD:
            legal = legal_action_mask(engine)
            assert not legal[48] and not legal[49] and not legal[50]


def test_action_space_derives_its_size_from_the_card_registry():
    """Default-settings sanity check -- see the sizing tests below for the enabled case. SKIP/GO/STOP
    sit right after every card id rather than at hardcoded indices, so enabling bonus cards can never
    collide a real card id with one of them (RULES.md #12)."""
    from engine.cards import NUM_CARDS
    from rl.action_space import ACTION_SIZE, GO, SKIP, STOP

    assert SKIP == NUM_CARDS
    assert GO == NUM_CARDS + 1
    assert STOP == NUM_CARDS + 2
    assert ACTION_SIZE == NUM_CARDS + 3


def test_action_space_resizes_correctly_with_bonus_cards_enabled():
    with _with_bonus_cards_and_rl_resized():
        from rl.action_space import ACTION_SIZE, GO, SKIP, STOP

        assert (SKIP, GO, STOP, ACTION_SIZE) == (51, 52, 53, 54)


def test_obs_size_derives_from_the_card_registry():
    from engine.cards import NUM_CARDS
    from rl.obs_encoding import NUM_SCALARS, OBS_SIZE, _DECISION_NODES

    assert OBS_SIZE == NUM_CARDS * 5 + NUM_SCALARS + len(_DECISION_NODES) + 1


def test_determinize_includes_bonus_cards_in_the_unseen_pool():
    """The old hardcoded range(48) would silently exclude bonus card ids from the sampled worlds,
    undercounting the opponent's hand/deck the moment one was actually out there unseen."""
    with _with_bonus_cards_and_rl_resized():
        from rl.action_space import apply_action, legal_action_mask
        from rl.baselines.heuristic_agent import heuristic_policy
        from rl.search import determinize

        engine = GoStopEngine(num_players=2, dealer=0, rng=random.Random(2))
        for _ in range(6):
            if engine.state.hand_over:
                break
            from rl.action_space import legal_action_mask as _mask
            import numpy as np
            legal = np.flatnonzero(_mask(engine))
            apply_action(engine, int(heuristic_policy(engine, legal)))
        if engine.state.hand_over:
            return  # rare seed where the hand ended within 6 plies; nothing to sample here
        me = engine.state.turn
        opp = 1 - me
        s = engine.state
        known = (set(s.players[me].hand) | set(s.field_cards())
                 | set(s.players[me].captured) | set(s.players[opp].captured))
        expected_unseen = set(range(51)) - known

        seen_bonus_ids_somewhere = False
        for seed in range(20):
            world = determinize(engine, me, random.Random(seed))
            sampled = set(world.state.players[opp].hand) | set(world.state.deck)
            assert sampled == expected_unseen  # conservation: exactly the unseen pool, every time
            if sampled & set(_BONUS_IDS):
                seen_bonus_ids_somewhere = True
        if expected_unseen & set(_BONUS_IDS):
            assert seen_bonus_ids_somewhere


def test_search_policy_plays_a_full_game_with_bonus_cards_enabled():
    with _with_bonus_cards_and_rl_resized():
        import numpy as np

        from rl.action_space import apply_action, legal_action_mask
        from rl.search import SearchPolicy

        engine = GoStopEngine(num_players=2, dealer=1, rng=random.Random(4))
        policy = SearchPolicy(determinizations=4, min_z=1.0, seed=1)
        steps = 0
        while not engine.state.hand_over:
            steps += 1
            assert steps < 200
            legal = np.flatnonzero(legal_action_mask(engine))
            action = policy(engine, legal)
            assert action in legal
            apply_action(engine, int(action))
        assert engine.state.result is not None


def test_draw_blind_replacement_removes_exactly_one_card_and_is_reproducible_per_seed():
    pile_a, pile_b = [1, 2, 3, 4, 5], [1, 2, 3, 4, 5]
    a = draw_blind_replacement(pile_a, random.Random(7))
    b = draw_blind_replacement(pile_b, random.Random(7))
    assert a == b
    assert pile_a == pile_b
    assert len(pile_a) == 4
    assert a not in pile_a or pile_a.count(a) == 0


# -- full-hand fuzz, mirroring test_full_hand_replay.py's conservation check ----------------------

def _all_accounted_cards(engine: GoStopEngine) -> list[int]:
    s = engine.state
    ids: list[int] = []
    for p in s.players:
        ids.extend(p.hand)
        ids.extend(p.captured)
    ids.extend(s.field_cards())
    ids.extend(s.deck)
    return ids


def test_full_hand_with_bonus_cards_conserves_all_51_cards_and_terminates():
    with _with_bonus_cards():
        for seed in range(30):
            rng = random.Random(seed)
            engine = GoStopEngine(num_players=2, dealer=0, rng=random.Random(seed))
            steps = 0
            while not engine.state.hand_over:
                steps += 1
                assert steps < 500, "hand did not terminate"
                assert sorted(_all_accounted_cards(engine)) == list(range(51))
                decision = engine.state.pending_decision
                if decision == DecisionNode.BOMB_DECISION:
                    bombs = engine.available_bombs()
                    if bombs and rng.random() < 0.5:
                        engine.declare_bomb(bombs[0])
                    else:
                        engine.skip_bomb()
                elif decision == DecisionNode.PLAY_CARD:
                    hand = sorted(engine.state.players[engine.state.turn].hand)
                    engine.play_card(rng.choice(hand))
                elif decision == DecisionNode.GO_STOP:
                    engine.go() if rng.random() < 0.5 else engine.stop()
                else:
                    raise AssertionError(f"unexpected pending decision: {decision}")
            assert sorted(_all_accounted_cards(engine)) == list(range(51))
