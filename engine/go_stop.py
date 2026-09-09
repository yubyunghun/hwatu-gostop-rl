"""Go/Stop decision flow and hand-ending paths (stop, nagari, deck-exhaustion).
See RULES.md sections 10-11. Settlement here assumes exactly 2 players -- full
3-player go/stop payment splitting is an explicit stretch-scope item (RULES.md #12)."""

from engine.rules_config import GO_STOP_MIN_SCORE
from engine.scoring import RawScore, score_player, settle
from engine.state import DecisionNode, Event, EventType, GameState, HandResult


def current_raw_score(state: GameState, player: int) -> RawScore:
    p = state.players[player]
    return score_player(p.captured, p.bonus_pi_received, p.bonus_pi_paid)


def check_go_stop_trigger(state: GameState, player: int) -> None:
    """Call after a player's turn resolves. Offers the GO_STOP decision whenever
    their score is at/above threshold -- including on every later turn where they
    add to an already-qualifying score, since real play lets them decide again."""
    raw = current_raw_score(state, player)
    if raw.total >= GO_STOP_MIN_SCORE:
        state.pending_decision = DecisionNode.GO_STOP
        state.scoring_player = player


def resolve_go(state: GameState) -> None:
    player = state.scoring_player
    state.players[player].go_count += 1
    state.emit(Event(EventType.GO, player, ()))
    state.scoring_player = None
    state.pending_decision = DecisionNode.PLAY_CARD


def resolve_stop(state: GameState) -> None:
    winner = state.scoring_player
    loser = state.opponents(winner)[0]
    _finish_hand(state, winner, loser)


def resolve_nagari(state: GameState) -> None:
    state.result = HandResult(winner=None, scores=[0] * state.num_players, nagari=True)
    state.hand_over = True
    state.pending_decision = DecisionNode.HAND_OVER
    state.emit(Event(EventType.NAGARI, None, ()))


def check_hands_exhausted_end(state: GameState) -> bool:
    """Call once every player's hand is empty (a hand ends when there's nothing left
    to play, regardless of whether the deck still has leftover undrawn cards -- deck
    and hand sizes don't have to divide evenly). Returns True if it ended the hand:
    the highest-scoring qualifying (>= GO_STOP_MIN_SCORE) player wins as if they'd
    stopped; if nobody ever qualified, the hand is nagari."""
    if any(state.players[p].hand for p in range(state.num_players)):
        return False
    raws = [current_raw_score(state, p) for p in range(state.num_players)]
    qualifying = [p for p, r in enumerate(raws) if r.total >= GO_STOP_MIN_SCORE]
    if not qualifying:
        resolve_nagari(state)
        return True
    winner = max(qualifying, key=lambda p: raws[p].total)
    loser = state.opponents(winner)[0]
    _finish_hand(state, winner, loser)
    return True


def _finish_hand(state: GameState, winner: int, loser: int) -> None:
    winner_raw = current_raw_score(state, winner)
    loser_raw = current_raw_score(state, loser)
    loser_called_go = state.players[loser].go_count > 0
    result = settle(winner, winner_raw, loser_raw, state.players[winner].go_count, loser_called_go)

    scores = [0] * state.num_players
    scores[winner] = result.final_score
    scores[loser] = -result.final_score

    state.result = HandResult(winner=winner, scores=scores)
    state.hand_over = True
    state.pending_decision = DecisionNode.HAND_OVER
    state.emit(Event(EventType.HAND_END, winner, (), note=f"final_score={result.final_score}"))
