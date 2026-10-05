"""Every rule-variant constant the engine uses. See RULES.md for sourcing and the
worked reasoning behind each value — change values there and here together."""

import os

# Section 2: dealing (RULES.md #2)
DEALING_TABLE: dict[int, dict[str, int]] = {
    2: {"hand": 10, "field": 6, "deck": 22},
    3: {"hand": 7, "field": 8, "deck": 19},
}
# If the initial field deal produces 3+ cards of one month, reshuffle and redeal
# rather than leave an unresolvable/degenerate starting pile.
REDEAL_ON_DEGENERATE_FIELD = True

# Section 2a: first-dealer draw (RULES.md #2a). "day" favors the latest month (and, on a tie, the
# highest-ranked card); "night" favors the earliest month (and the lowest-ranked card on a tie).
FIRST_DEALER_TIME_OF_DAY = "day"

# Section 4/5/6/7: capture bonuses (RULES.md #4-7)
SWEEP_BONUS_PI = 1
PPEOK_RULESET = "LOCK_AND_PENALTY"
PPEOK_PENALTY_PI = 1
TTADAK_BONUS_MODE = "SAME_TURN_DOUBLE_CAPTURE"
TTADAK_PENALTY_PI = 1
BOMB_MODE = "THREE_IN_HAND_PLUS_FIELD"
BOMB_PENALTY_PI = 1

# Section 8: scoring (RULES.md #8)
GO_STOP_MIN_SCORE = 7
RAIN_GWANG_PENALTY = 1  # subtracted only from the exactly-3-gwang case when rain is among them
GODORI_BONUS = 5
RIBBON_SET_BONUS = 3
ANIMAL_SCORE_THRESHOLD = 5
RIBBON_SCORE_THRESHOLD = 5
PI_SCORE_THRESHOLD = 10
GWANG_SCORE_TABLE = {5: 15, 4: 4, 3: 3}  # 3-gwang value before RAIN_GWANG_PENALTY is applied

# Section 9: multiplier penalties (RULES.md #9)
GWANG_BAK_THRESHOLD = 0  # opponent gwang count <= this -> gwang-bak
PI_BAK_THRESHOLD = 5  # opponent pi count < this -> pi-bak
MEONG_BAK_THRESHOLD = 7  # winner animal count >= this -> meong-bak

# Section 10: go/stop (RULES.md #10)
GO_BONUS_POINTS = 1
GO_MULTIPLIER_START = 3  # multiplier = 2 ** max(0, go_count - (GO_MULTIPLIER_START - 1))
GOBAK_ENABLED = True
GOBAK_MULTIPLIER = 2

# Section 11: nagari (RULES.md #11) — same-dealer-redeals is implemented at the API session layer
# (api/session_manager.py); nothing currently multiplies by this, see RULES.md #11.
NAGARI_STAKE_MULTIPLIER = 2

# Section 12: deferred, not implemented in v1 (RULES.md #12)
HEUNDEUL_ENABLED = False

# Bonus cards are fully implemented (engine, dealing, scoring, search -- RULES.md #12) but default to
# off, because this constant sizes the global card registry (engine/cards.py:CARDS) that every
# trained checkpoint under checkpoints*/ was produced against; flipping it process-wide would make
# those checkpoints' saved network shapes stop matching. An env var lets a server process opt in
# (e.g. `HWATU_NUM_BONUS_CARDS=3 uvicorn api.main:app`) without moving the shared default that the
# training/eval scripts and test suite run against.
NUM_BONUS_CARDS = int(os.environ.get("HWATU_NUM_BONUS_CARDS", "0"))
BONUS_CARD_PI_VALUE = 2  # pinned value once enabled: counts like a ssangpi (double-junk) card
