"""GoStopEngine: the single orchestrator both the RL environment (rl/env.py) and the
API (api/bot_inference.py) drive, so training and serving can never diverge on rules.
See RULES.md section 3 for the turn-structure this implements."""

import random

from engine.bombs import available_bomb_months, resolve_bomb
from engine.capture import resolve_draw, resolve_hand_play
from engine.dealing import deal_new_hand
from engine.go_stop import check_go_stop_trigger, check_hands_exhausted_end, resolve_go, resolve_stop
from engine.state import DecisionNode, GameState


class GoStopEngine:
    def __init__(self, num_players: int = 2, dealer: int = 0, rng: random.Random | None = None):
        self.state: GameState = deal_new_hand(num_players, dealer, rng)
        self._enter_turn()

    # -- turn-structure plumbing -------------------------------------------------

    def _enter_turn(self) -> None:
        s = self.state
        if s.hand_over:
            return
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
        s = self.state
        if s.deck:
            drawn = s.deck.pop(0)
            resolve_draw(s, s.turn, drawn)
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
        if s.pending_decision == DecisionNode.GO_STOP:
            return ["GO", "STOP"]
        return []
