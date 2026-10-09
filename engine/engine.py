"""GoStopEngine: the single orchestrator both the RL environment (rl/env.py) and the
API (api/bot_inference.py) drive, so training and serving can never diverge on rules.
See RULES.md section 3 for the turn-structure this implements."""

import random

from engine.bombs import available_bomb_months, resolve_bomb
from engine.capture import resolve_capture_choice, resolve_draw, resolve_hand_play
from engine.cards import Category, card
from engine.dealing import deal_new_hand, draw_blind_replacement
from engine.go_stop import check_go_stop_trigger, check_hands_exhausted_end, resolve_go, resolve_stop
from engine.state import DecisionNode, Event, EventType, GameState


class GoStopEngine:
    def __init__(self, num_players: int = 2, dealer: int = 0, rng: random.Random | None = None):
        # Kept (not just used once at deal time) so a bonus card banked mid-hand (RULES.md #12) draws
        # its blind replacement from the same continuous rng stream as everything else.
        self._rng = rng or random.Random()
        self.state: GameState = deal_new_hand(num_players, dealer, self._rng)
        self._enter_turn()

    # -- turn-structure plumbing -------------------------------------------------

    def _resolve_bonus_cards_in_hand(self, player: int) -> None:
        """At the start of a turn, any bonus card already sitting in that player's hand is banked for
        a blind replacement draw (RULES.md #12). This is never modeled as a real decision -- banking
        it is never worse than holding it, so there's nothing to choose.

        Loops rather than a single pass: the blind replacement itself can be another bonus card, and
        that one needs resolving too, same as the initial-deal cascade in
        engine/dealing.py:_resolve_initial_bonus_cards."""
        s = self.state
        hand = s.players[player].hand
        while True:
            bonus_ids = [cid for cid in hand if card(cid).category is Category.BONUS]
            if not bonus_ids:
                return
            for cid in bonus_ids:
                hand.discard(cid)
                s.players[player].captured.append(cid)
                s.emit(Event(EventType.BONUS_CARD, player, (cid,)))
                if s.deck:
                    hand.add(draw_blind_replacement(s.deck, self._rng))

    def _enter_turn(self) -> None:
        s = self.state
        if s.hand_over:
            return
        self._resolve_bonus_cards_in_hand(s.turn)
        if not s.players[s.turn].hand:
            # Hand emptied early (bombs consume 3 hand cards in one turn, so hands
            # can go out of lockstep). This player just resolves the forced deck
            # draw each remaining turn until the hand ends -- see RULES.md section 7.
            self._after_hand_play()
            return
        if available_bomb_months(s, s.turn):
            s.pending_decision = DecisionNode.BOMB_DECISION
        else:
            s.pending_decision = DecisionNode.PLAY_CARD

    def _after_hand_play(self) -> None:
        """The forced post-play draw. Pauses instead of finishing the turn if the draw itself landed
        on a field pile of exactly 2 same-month cards (RULES.md #4) -- see choose_capture, which
        resumes at _finish_turn_after_draw once that's answered."""
        s = self.state
        if s.deck:
            drawn = s.deck.pop(0)
            resolve_draw(s, s.turn, drawn)
            if s.pending_decision == DecisionNode.CAPTURE_CHOICE:
                return
        self._finish_turn_after_draw()

    def _finish_turn_after_draw(self) -> None:
        s = self.state
        if check_hands_exhausted_end(s):
            return
        check_go_stop_trigger(s, s.turn)
        if s.pending_decision != DecisionNode.GO_STOP:
            self._advance_turn()

    def _advance_turn(self) -> None:
        s = self.state
        s.turn = (s.turn + 1) % s.num_players
        self._enter_turn()

    # -- public actions -----------------------------------------------------------

    def available_bombs(self) -> list[int]:
        return available_bomb_months(self.state, self.state.turn)

    def declare_bomb(self, month: int) -> None:
        s = self.state
        if s.pending_decision != DecisionNode.BOMB_DECISION:
            raise ValueError(f"not expecting a bomb decision (pending={s.pending_decision})")
        resolve_bomb(s, s.turn, month)
        # The bomb itself is always a deterministic capture-all-4 (RULES.md #7) -- but the forced
        # draw that follows can still land on an unrelated 2-card pile and need a CAPTURE_CHOICE.
        self._after_hand_play()

    def skip_bomb(self) -> None:
        s = self.state
        if s.pending_decision != DecisionNode.BOMB_DECISION:
            raise ValueError(f"not expecting a bomb decision (pending={s.pending_decision})")
        s.pending_decision = DecisionNode.PLAY_CARD

    def play_card(self, card_id: int) -> None:
        s = self.state
        if s.pending_decision != DecisionNode.PLAY_CARD:
            raise ValueError(f"not expecting a card play (pending={s.pending_decision})")
        if card_id not in s.players[s.turn].hand:
            raise ValueError(f"player {s.turn} does not hold card {card_id}")
        resolve_hand_play(s, s.turn, card_id)
        if s.pending_decision == DecisionNode.CAPTURE_CHOICE:
            return  # matched 2 field cards (RULES.md #4); wait for choose_capture() before drawing
        self._after_hand_play()

    def choose_capture(self, field_card_id: int) -> None:
        """Resolves a CAPTURE_CHOICE (RULES.md #4): which of 2 same-month field cards to pair with.
        Can come up twice in the same turn (the hand-play and the forced draw can each independently
        land on a different month's 2-card pile), so this always re-dispatches through the normal
        pending_decision machinery rather than assuming what comes next."""
        s = self.state
        if s.pending_decision != DecisionNode.CAPTURE_CHOICE:
            raise ValueError(f"not expecting a capture choice (pending={s.pending_decision})")
        resolve_capture_choice(s, s.turn, field_card_id)
        # Reset before resuming: _after_hand_play/_finish_turn_after_draw check pending_decision for
        # a *new* CAPTURE_CHOICE (the draw or end-of-turn step can independently land on its own
        # 2-card pile); leaving the one just answered in place would look like it was never resolved.
        s.pending_decision = DecisionNode.PLAY_CARD
        if s.capture_choice_after_draw:
            self._finish_turn_after_draw()
        else:
            self._after_hand_play()

    def go(self) -> None:
        s = self.state
        if s.pending_decision != DecisionNode.GO_STOP:
            raise ValueError(f"not expecting a go/stop decision (pending={s.pending_decision})")
        resolve_go(s)
        self._advance_turn()

    def stop(self) -> None:
        s = self.state
        if s.pending_decision != DecisionNode.GO_STOP:
            raise ValueError(f"not expecting a go/stop decision (pending={s.pending_decision})")
        resolve_stop(s)

    # -- introspection used by CLI / RL / API consumers ---------------------------

    def legal_options(self) -> list:
        s = self.state
        if s.pending_decision == DecisionNode.PLAY_CARD:
            return sorted(s.players[s.turn].hand)
        if s.pending_decision == DecisionNode.BOMB_DECISION:
            return list(self.available_bombs()) + ["SKIP"]
        if s.pending_decision == DecisionNode.CAPTURE_CHOICE:
            return sorted(s.pending_capture_choice[1])
        if s.pending_decision == DecisionNode.GO_STOP:
            return ["GO", "STOP"]
        return []
