import numpy as np
from fastapi.testclient import TestClient

from api.deps import get_bot_policy, get_session_manager
from api.main import app
from api.session_manager import SessionManager
from engine.state import DecisionNode
from rl.baselines.random_agent import random_policy


def _fresh_client():
    """A TestClient with its own SessionManager and a fast random bot policy,
    so API tests don't share state across tests or pay for loading a real model.
    The SessionManager instance must be created once and reused across requests
    within a test -- a fresh one per call would make every session vanish."""
    return _fresh_client_with_manager()[0]


def _fresh_client_with_manager():
    """Like `_fresh_client`, but also hands back the SessionManager so a test can reach into a live
    session's engine state directly (e.g. to force a scenario that's rare under a fixed seed)."""
    manager = SessionManager()
    app.dependency_overrides[get_session_manager] = lambda: manager
    app.dependency_overrides[get_bot_policy] = lambda: random_policy
    return TestClient(app), manager


def test_health():
    client = _fresh_client()
    assert client.get("/health").json() == {"status": "ok"}


def test_list_cards_returns_48():
    client = _fresh_client()
    resp = client.get("/cards")
    assert resp.status_code == 200
    assert len(resp.json()) == 48


def test_create_session_returns_state_where_it_is_the_humans_turn_or_hand_is_over():
    client = _fresh_client()
    resp = client.post("/sessions", json={"human_seat": 0, "seed": 1})
    assert resp.status_code == 200
    state = resp.json()
    assert state["viewer_seat"] == 0
    assert state["hand_over"] or state["turn"] == 0


def test_create_session_never_exposes_the_bots_hand():
    client = _fresh_client()
    resp = client.post("/sessions", json={"human_seat": 0, "seed": 1})
    state = resp.json()
    bot_player = next(p for p in state["players"] if p["seat"] != 0)
    assert bot_player["hand"] is None
    assert bot_player["hand_count"] > 0
    human_player = next(p for p in state["players"] if p["seat"] == 0)
    assert human_player["hand"] is not None
    assert len(human_player["hand"]) == human_player["hand_count"]


def test_action_endpoint_rejects_illegal_card():
    client = _fresh_client()
    resp = client.post("/sessions", json={"human_seat": 0, "seed": 1})
    state = resp.json()
    if state["hand_over"]:
        return  # rare seed where the hand auto-ends immediately; nothing to test here
    bad_card = next(c for c in range(48) if c not in (state["players"][0]["hand"] or []))
    action_resp = client.post(f"/sessions/{state['session_id']}/actions",
                               json={"type": "play_card", "card_id": bad_card})
    assert action_resp.status_code == 400


def test_full_session_can_be_played_to_completion_via_the_api():
    client = _fresh_client()
    resp = client.post("/sessions", json={"human_seat": 0, "seed": 3})
    state = resp.json()
    rng = np.random.default_rng(3)
    steps = 0
    while not state["hand_over"]:
        steps += 1
        assert steps < 200, "API-driven hand did not terminate"
        decision = state["pending_decision"]
        options = state["legal_options"]
        assert options, "it's the human's turn but no legal options were returned"
        if decision == DecisionNode.PLAY_CARD.name:
            req = {"type": "play_card", "card_id": int(rng.choice(options))}
        elif decision == DecisionNode.BOMB_DECISION.name:
            choice = rng.choice(options)
            # legal_options() for BOMB_DECISION is already a list of month numbers (plus "SKIP"),
            # not card ids -- see GoStopEngine.legal_options()/available_bombs().
            req = {"type": "skip_bomb"} if choice == "SKIP" else {"type": "declare_bomb", "month": int(choice)}
        else:  # GO_STOP
            req = {"type": "go"} if rng.random() < 0.5 else {"type": "stop"}
        action_resp = client.post(f"/sessions/{state['session_id']}/actions", json=req)
        assert action_resp.status_code == 200
        state = action_resp.json()
    assert state["result"] is not None


def test_get_session_matches_post_action_response():
    client = _fresh_client()
    resp = client.post("/sessions", json={"human_seat": 0, "seed": 1})
    state = resp.json()
    fetched = client.get(f"/sessions/{state['session_id']}").json()
    assert fetched == state


def test_unknown_session_is_404():
    client = _fresh_client()
    assert client.get("/sessions/does-not-exist").status_code == 404


def test_bomb_decision_legal_option_is_a_month_directly_usable_in_the_request():
    """legal_options() for BOMB_DECISION returns month numbers, not card ids (see
    GoStopEngine.legal_options()); a client must be able to send one straight back as `month`
    without any conversion. Forced directly rather than hoping a fixed seed produces a bomb -- that
    silently never happened to trigger across this suite's existing seeds until bonus cards made it
    likely enough to notice (see RULES.md #12's bonus-card section)."""
    client, manager = _fresh_client_with_manager()
    resp = client.post("/sessions", json={"human_seat": 0, "seed": 1})
    state = resp.json()
    session = manager.get(state["session_id"])
    engine = session.engine

    # Force a bomb: 3 hand cards of May (ids 16-19 minus one) plus the 4th sitting alone on the field.
    engine.state.players[0].hand |= {16, 17, 18}
    engine.state.field[5] = [19]
    engine.state.turn = 0
    engine._enter_turn()
    assert engine.state.pending_decision.name == "BOMB_DECISION"

    fetched = client.get(f"/sessions/{state['session_id']}").json()
    assert 5 in fetched["legal_options"]  # the month, not a card id

    action_resp = client.post(f"/sessions/{state['session_id']}/actions",
                               json={"type": "declare_bomb", "month": 5})
    assert action_resp.status_code == 200, action_resp.text


def test_next_hand_rejects_a_hand_still_in_progress():
    client = _fresh_client()
    resp = client.post("/sessions", json={"human_seat": 0, "seed": 1})
    state = resp.json()
    if state["hand_over"]:
        return  # rare seed where the hand auto-ends immediately; nothing to test here
    next_resp = client.post(f"/sessions/{state['session_id']}/next_hand")
    assert next_resp.status_code == 409


def test_next_hand_continues_the_match_with_accumulated_scores():
    client = _fresh_client()
    resp = client.post("/sessions", json={"human_seat": 0, "seed": 3})
    state = resp.json()
    rng = np.random.default_rng(3)
    steps = 0
    while not state["hand_over"]:
        steps += 1
        assert steps < 200, "API-driven hand did not terminate"
        decision = state["pending_decision"]
        options = state["legal_options"]
        if decision == DecisionNode.PLAY_CARD.name:
            req = {"type": "play_card", "card_id": int(rng.choice(options))}
        elif decision == DecisionNode.BOMB_DECISION.name:
            choice = rng.choice(options)
            req = {"type": "skip_bomb"} if choice == "SKIP" else {"type": "declare_bomb", "month": int(choice)}
        else:  # GO_STOP
            req = {"type": "go"} if rng.random() < 0.5 else {"type": "stop"}
        state = client.post(f"/sessions/{state['session_id']}/actions", json=req).json()
    assert state["match_scores"] == [0, 0]  # nothing banked until a hand actually finishes

    next_resp = client.post(f"/sessions/{state['session_id']}/next_hand")
    assert next_resp.status_code == 200
    new_state = next_resp.json()
    assert new_state["session_id"] == state["session_id"]
    assert new_state["match_scores"] == state["result"]["scores"]
    assert not new_state["hand_over"] or new_state["result"] is not None
