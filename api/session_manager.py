"""In-memory game sessions. No database -- an explicit non-goal for this project
(see project plan); sessions live for the lifetime of the server process."""

import random
import uuid

from engine.cards import card
from engine.engine import GoStopEngine
from engine.go_stop import current_raw_score

from api.schemas import CardOut, EventOut, GameStateOut, PlayerOut, ResultOut


class Session:
    def __init__(self, session_id: str, engine: GoStopEngine, human_seat: int):
        self.session_id = session_id
        self.engine = engine
        self.human_seat = human_seat
        self.bot_seat = engine.state.opponents(human_seat)[0]


class SessionManager:
    def __init__(self):
        self._sessions: dict[str, Session] = {}

    def create(self, human_seat: int = 0, seed: int | None = None) -> Session:
        rng = random.Random(seed)
        engine = GoStopEngine(num_players=2, dealer=0, rng=rng)
        session_id = str(uuid.uuid4())
        session = Session(session_id, engine, human_seat)
        self._sessions[session_id] = session
        return session

    def get(self, session_id: str) -> Session:
        if session_id not in self._sessions:
            raise KeyError(f"no such session: {session_id}")
        return self._sessions[session_id]


def card_out(card_id: int) -> CardOut:
    c = card(card_id)
    return CardOut(id=c.id, month=c.month, category=c.category.value, name=c.name)


def serialize_state(session: Session, recent_event_count: int = 5) -> GameStateOut:
    """Redacts any hand that isn't the viewer's (human_seat) own -- a client must
    never receive another player's hidden hand contents over the wire."""
    engine = session.engine
    s = engine.state
    viewer = session.human_seat

    players = []
    for seat, p in enumerate(s.players):
        hand = sorted(p.hand) if seat == viewer else None
        players.append(PlayerOut(
            seat=seat, hand=hand, hand_count=len(p.hand), captured=sorted(p.captured),
            go_count=p.go_count, score=current_raw_score(s, seat).total,
        ))

    legal_options = engine.legal_options() if s.turn == viewer and not s.hand_over else []

    result = None
    if s.result is not None:
        result = ResultOut(winner=s.result.winner, scores=s.result.scores, nagari=s.result.nagari)

    recent_events = [
        EventOut(type=e.type.name, player=e.player, card_ids=list(e.card_ids),
                  pi_penalty=e.pi_penalty, note=e.note)
        for e in s.events[-recent_event_count:]
    ]

    return GameStateOut(
        session_id=session.session_id, viewer_seat=viewer, turn=s.turn,
        pending_decision=s.pending_decision.name, legal_options=legal_options,
        players=players, field=sorted(s.field_cards()), deck_count=len(s.deck),
        hand_over=s.hand_over, result=result, recent_events=recent_events,
    )
