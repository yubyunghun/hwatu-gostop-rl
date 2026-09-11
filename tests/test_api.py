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
    manager = SessionManager()
    app.dependency_overrides[get_session_manager] = lambda: manager
    app.dependency_overrides[get_bot_policy] = lambda: random_policy
    return TestClient(app)


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
            req = {"type": "skip_bomb"} if choice == "SKIP" else {"type": "declare_bomb", "month": None}
            if req["type"] == "declare_bomb":
                from engine.cards import month_of
                req["month"] = month_of(int(choice))
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
