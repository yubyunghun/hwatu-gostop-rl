"""Human-vs-human terminal Go-Stop, for manually sanity-checking the rules engine
before any RL/ML code touches it. Run from the project root:

    .venv\\Scripts\\python.exe scripts\\play_cli.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to a codepage that can't print 월/광/etc.

from engine.cards import card
from engine.engine import GoStopEngine
from engine.go_stop import current_raw_score
from engine.state import DecisionNode


def describe(card_id: int) -> str:
    c = card(card_id)
    return f"{card_id}:{c.month}월-{c.category.value}-{c.name}"


def print_board(engine: GoStopEngine) -> None:
    s = engine.state
    print("\n" + "=" * 60)
    for p in range(s.num_players):
        marker = " <- turn" if p == s.turn else ""
        raw = current_raw_score(s, p)
        print(f"P{p} hand ({len(s.players[p].hand)}): "
              f"{', '.join(describe(c) for c in sorted(s.players[p].hand))}{marker}")
        print(f"   captured ({len(s.players[p].captured)}): "
              f"{', '.join(describe(c) for c in sorted(s.players[p].captured))} "
              f"[score={raw.total} go={s.players[p].go_count}]")
    field_ids = [cid for pile in s.field.values() for cid in sorted(pile)]
    print(f"Field: {', '.join(describe(c) for c in sorted(field_ids))}")
    print(f"Deck remaining: {len(s.deck)}")
    if s.events:
        print("Last events: " + "; ".join(
            f"{e.type.name}({','.join(map(str, e.card_ids))})" for e in s.events[-3:]))


def prompt_int(msg: str, options: list[int]) -> int:
    while True:
        raw = input(f"{msg} {options}: ").strip()
        try:
            val = int(raw)
        except ValueError:
            continue
        if val in options:
            return val


def main() -> None:
    engine = GoStopEngine(num_players=2, dealer=0)
    while not engine.state.hand_over:
        print_board(engine)
        decision = engine.state.pending_decision
        turn = engine.state.turn

        if decision == DecisionNode.BOMB_DECISION:
            bombs = engine.available_bombs()
            print(f"P{turn}: bomb available for month(s) {bombs}. Enter month to bomb, or -1 to skip.")
            choice = prompt_int("Bomb month", bombs + [-1])
            if choice == -1:
                engine.skip_bomb()
            else:
                engine.declare_bomb(choice)
        elif decision == DecisionNode.PLAY_CARD:
            hand = sorted(engine.state.players[turn].hand)
            choice = prompt_int(f"P{turn}: play which card?", hand)
            engine.play_card(choice)
        elif decision == DecisionNode.GO_STOP:
            print(f"P{turn} has reached the scoring threshold. 1 = GO, 0 = STOP")
            choice = prompt_int("Go or stop?", [0, 1])
            engine.go() if choice == 1 else engine.stop()

    print_board(engine)
    result = engine.state.result
    if result.nagari:
        print("Nagari -- deck exhausted with no qualifying score. No payment this hand.")
    else:
        print(f"Player {result.winner} wins! Scores: {result.scores}")


if __name__ == "__main__":
    main()
