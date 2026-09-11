"""Thin FastAPI session/inference layer. Deliberately reuses engine.py,
action_space.py, and obs_encoding.py completely unchanged from training (via
bot_inference.py -> rl/model_agent.py) -- see project plan: this is what
guarantees a served bot plays by the exact rules and observation shape it was
trained under, with no second implementation to drift out of sync.
"""

import numpy as np
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from engine.cards import CARDS
from engine.state import DecisionNode
from rl.action_space import apply_action, legal_action_mask

from api.deps import get_bot_policy, get_session_manager
from api.schemas import ActionRequest, CreateSessionRequest, GameStateOut
from api.session_manager import Session, SessionManager, card_out, serialize_state

app = FastAPI(title="Go-Stop API")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


def _run_bot_turns(session: Session, bot_policy) -> None:
    engine = session.engine
    s = engine.state
    while not s.hand_over and s.turn == session.bot_seat:
        legal = np.flatnonzero(legal_action_mask(engine))
        action = bot_policy(engine, legal)
        apply_action(engine, int(action))


def _apply_human_action(session: Session, req: ActionRequest) -> None:
    engine = session.engine
    s = engine.state
    if s.hand_over:
        raise HTTPException(409, "hand is already over")
    if s.turn != session.human_seat:
        raise HTTPException(409, "not your turn")
    decision = s.pending_decision

    try:
        if req.type == "play_card":
            if decision != DecisionNode.PLAY_CARD or req.card_id is None:
                raise HTTPException(400, "play_card is not valid for the current decision")
            engine.play_card(req.card_id)
        elif req.type == "declare_bomb":
            if decision != DecisionNode.BOMB_DECISION or req.month is None:
                raise HTTPException(400, "declare_bomb is not valid for the current decision")
            engine.declare_bomb(req.month)
        elif req.type == "skip_bomb":
            if decision != DecisionNode.BOMB_DECISION:
                raise HTTPException(400, "skip_bomb is not valid for the current decision")
            engine.skip_bomb()
        elif req.type == "go":
            if decision != DecisionNode.GO_STOP:
                raise HTTPException(400, "go is not valid for the current decision")
            engine.go()
        elif req.type == "stop":
            if decision != DecisionNode.GO_STOP:
                raise HTTPException(400, "stop is not valid for the current decision")
            engine.stop()
        else:
            raise HTTPException(400, f"unknown action type: {req.type}")
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/cards")
def list_cards():
    return [card_out(c.id) for c in CARDS]


@app.post("/sessions", response_model=GameStateOut)
def create_session(req: CreateSessionRequest, manager: SessionManager = Depends(get_session_manager),
                    bot_policy=Depends(get_bot_policy)):
    session = manager.create(human_seat=req.human_seat, seed=req.seed)
    _run_bot_turns(session, bot_policy)
    return serialize_state(session)


@app.get("/sessions/{session_id}", response_model=GameStateOut)
def get_session(session_id: str, manager: SessionManager = Depends(get_session_manager)):
    try:
        session = manager.get(session_id)
    except KeyError:
        raise HTTPException(404, "session not found")
    return serialize_state(session)


@app.post("/sessions/{session_id}/actions", response_model=GameStateOut)
def submit_action(session_id: str, req: ActionRequest,
                   manager: SessionManager = Depends(get_session_manager),
                   bot_policy=Depends(get_bot_policy)):
    try:
        session = manager.get(session_id)
    except KeyError:
        raise HTTPException(404, "session not found")
    _apply_human_action(session, req)
    _run_bot_turns(session, bot_policy)
    return serialize_state(session)
