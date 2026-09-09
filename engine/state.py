"""Core mutable game-state types shared by every rule module. Pure data + a couple of
tiny helpers — no rule logic lives here (see capture.py/bombs.py/scoring.py/go_stop.py)."""

from dataclasses import dataclass, field
from enum import Enum, auto


class DecisionNode(Enum):
    PLAY_CARD = auto()
    BOMB_DECISION = auto()
    GO_STOP = auto()
    HAND_OVER = auto()


class EventType(Enum):
    FIELD_ADD = auto()
    CAPTURE = auto()
    SWEEP = auto()
    PPEOK_LOCK = auto()
    TTADAK = auto()
    BOMB = auto()
    GO = auto()
    STOP = auto()
    NAGARI = auto()
    HAND_END = auto()


@dataclass(frozen=True)
class Event:
    type: EventType
    player: int | None
    card_ids: tuple[int, ...]
    pi_penalty: int = 0
    note: str = ""


@dataclass
class PlayerState:
    hand: set[int] = field(default_factory=set)
    captured: list[int] = field(default_factory=list)
    go_count: int = 0
    bonus_pi_received: int = 0
    bonus_pi_paid: int = 0


@dataclass
class HandResult:
    winner: int | None  # None if nagari
    scores: list[int]
    nagari: bool = False


@dataclass
class GameState:
    num_players: int
    deck: list[int]
    field: dict[int, list[int]]  # month -> card ids currently sitting on the field
    players: list[PlayerState]
    turn: int
    dealer: int
    pending_decision: DecisionNode = DecisionNode.PLAY_CARD
    events: list[Event] = field(default_factory=list)
    hand_over: bool = False
    result: HandResult | None = None
    scoring_player: int | None = None  # whose GO_STOP decision is currently pending
    pending_pair: tuple[int, int] | None = None  # (hand_card_id, field_card_id) awaiting draw resolution for ppeok check
    ttadak_watch_month: int | None = None  # month just fully captured (3 cards) via hand-play this turn

    def opponents(self, player: int) -> list[int]:
        return [p for p in range(self.num_players) if p != player]

    def field_cards(self) -> list[int]:
        return [cid for pile in self.field.values() for cid in pile]

    def emit(self, event: Event) -> None:
        self.events.append(event)
