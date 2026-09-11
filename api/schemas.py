"""Pydantic response/request models. GameStateOut is deliberately redacted per
viewer -- see serialize_state() in session_manager.py -- so the wire format never
carries hidden information (another player's hand) to a client that shouldn't see it.
"""

from pydantic import BaseModel


class CardOut(BaseModel):
    id: int
    month: int
    category: str
    name: str


class PlayerOut(BaseModel):
    seat: int
    hand: list[int] | None  # None (hidden) for any seat other than the viewer
    hand_count: int
    captured: list[int]
    go_count: int
    score: int


class EventOut(BaseModel):
    type: str
    player: int | None
    card_ids: list[int]
    pi_penalty: int
    note: str


class ResultOut(BaseModel):
    winner: int | None
    scores: list[int]
    nagari: bool


class GameStateOut(BaseModel):
    session_id: str
    viewer_seat: int
    turn: int
    pending_decision: str
    legal_options: list
    players: list[PlayerOut]
    field: list[int]
    deck_count: int
    hand_over: bool
    result: ResultOut | None
    recent_events: list[EventOut]


class CreateSessionRequest(BaseModel):
    human_seat: int = 0
    seed: int | None = None


class ActionRequest(BaseModel):
    type: str  # "play_card" | "declare_bomb" | "skip_bomb" | "go" | "stop"
    card_id: int | None = None
    month: int | None = None
