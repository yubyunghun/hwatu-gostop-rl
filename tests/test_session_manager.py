from api.session_manager import SessionManager
from engine.state import HandResult


def test_next_hand_rejects_a_hand_still_in_progress():
    manager = SessionManager()
    session = manager.create(human_seat=0, seed=1)
    if session.engine.state.hand_over:
        return  # rare seed where the hand auto-ends immediately; nothing to test here
    try:
        session.next_hand()
        assert False, "expected a ValueError"
    except ValueError:
        pass


def test_next_hand_rotates_the_dealer_to_the_winner_and_accumulates_match_scores():
    manager = SessionManager()
    session = manager.create(human_seat=0, seed=1)
    s = session.engine.state
    s.hand_over = True
    s.result = HandResult(winner=1, scores=[-20, 20])

    session.next_hand()

    assert session.match_scores == [-20, 20]
    assert session.engine.state.dealer == 1
    assert session.engine.state.turn == (1 + 1) % 2  # first_turn = (dealer + 1) % num_players
    assert session.bot_seat == 1  # seat assignment is fixed for the sitting, dealer rotation aside


def test_next_hand_keeps_the_same_dealer_and_pays_nothing_on_nagari():
    manager = SessionManager()
    session = manager.create(human_seat=0, seed=1)
    s = session.engine.state
    previous_dealer = s.dealer
    s.hand_over = True
    s.result = HandResult(winner=None, scores=[0, 0], nagari=True)

    session.next_hand()

    assert session.match_scores == [0, 0]
    assert session.engine.state.dealer == previous_dealer


def test_next_hand_accumulates_across_more_than_two_hands():
    manager = SessionManager()
    session = manager.create(human_seat=0, seed=2)
    for scores in ([-10, 10], [15, -15]):
        s = session.engine.state
        s.hand_over = True
        s.result = HandResult(winner=0 if scores[0] > 0 else 1, scores=scores)
        session.next_hand()
    assert session.match_scores == [5, -5]
