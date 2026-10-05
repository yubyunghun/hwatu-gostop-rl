# Go-Stop (고스톱) Rules — Pinned Reference

Go-Stop has real regional/house-rule variation. This document is the single source of truth for
every rule decision the engine implements. Every constant named here lives in
`engine/rules_config.py` — nowhere else in the codebase should a rule constant be hardcoded.

Sources cross-checked: [pagat.com/fishing/gostop.html](https://www.pagat.com/fishing/gostop.html)
(Games Museum / John McLeod, generally the most careful English-language card-rules reference),
[gostopguide.com/gostop](https://gostopguide.com/gostop), and the
[Hanafuda](https://en.wikipedia.org/wiki/Hanafuda) Wikipedia article for the base 48-card structure
(Korean hwatu is Hanafuda with month 11 and month 12 swapped as whole suits, per pagat: "the months
of November and December have been switched").

## 1. Deck composition (48 cards, pinned)

12 months x 4 cards. Category totals: 5 gwang (bright), 9 yeol (animal), 10 ddi (ribbon),
24 physical pi (junk) cards — of which 2 are ssangpi (double-junk, worth 2 toward pi-count scoring).
`5 + 9 + 10 + 24 = 48`. This exact split is corroborated by both pagat and an independent Korean
source ("5 gwang, 9 animal, 10 ribbon, and the remaining 22 non-double + 2 double pi cards").

| Month | Gwang | Animal | Ribbon | Junk |
|---|---|---|---|---|
| 1 (Pine, 송학) | crane+sun | — | hongdan (red) | pi, pi |
| 2 (Plum, 매조) | — | bush warbler *(godori)* | hongdan (red) | pi, pi |
| 3 (Cherry, 벚꽃) | curtain | — | hongdan (red) | pi, pi |
| 4 (Wisteria, 흑싸리) | — | cuckoo *(godori)* | chodan (plain) | pi, pi |
| 5 (Iris, 난초) | — | bridge/animal | chodan (plain) | pi, pi |
| 6 (Peony, 모란) | — | butterflies | cheongdan (blue) | pi, pi |
| 7 (Clover, 홍싸리) | — | boar | chodan (plain) | pi, pi |
| 8 (Pampas, 공산) | full moon | geese *(godori)* | — (none) | pi, pi |
| 9 (Chrysanthemum, 국화) | — | sake cup | cheongdan (blue) | pi, pi |
| 10 (Maple, 단풍) | — | deer | cheongdan (blue) | pi, pi |
| 11 (Paulownia, 오동) | phoenix | — | — (none) | pi, pi, **ssangpi** |
| 12 (Rain, 비) | rain man | swallow | plain ribbon (ungrouped) | **ssangpi** |

- **Godori** = the 3 bird animal cards: February (bush warbler), April (cuckoo), August (geese).
- **Ssangpi** (double-junk, counts as 2 toward pi-count scoring): the November colored junk card
  and the December rain junk card. Pinned per pagat: "The December (rain) junk card and the
  coloured November (paulownia) junk card each count as two junk cards."
- **Ribbon color sets** (each is a specific named set of exactly 3 cards; the December ribbon is
  deliberately in no set): hongdan = {1,2,3}, chodan = {4,5,7}, cheongdan = {6,9,10}.
- Month 8 and month 11 have no ribbon card; month 8 and month 11 (and month 12, whose ribbon isn't
  in a color set) are the reason ribbon totals to 10, not 12.

## 2. Dealing (`DEALING_TABLE`, keyed by player count)

| Players | Hand (each) | Field | Deck |
|---|---|---|---|
| 2 | 10 | 6 | 22 |
| 3 | 7 | 8 | 19 |

3-player numbers are pagat-confirmed directly ("each player gets 7 cards in hand, 8 cards lie
face-up on the floor, the remaining 19 form the deck"). 2-player numbers are the standard matgo
deal and check out arithmetically (10*2 + 6 + 22 = 48). **v1 targets 2 players only** (see project
plan); the table is still keyed by player count so the engine isn't hardcoded to one size.

### 2a. Choosing the first dealer

Pagat and Wikipedia agree on the method and disagree on nothing material, so this is pinned as-is.
Each player draws one card from the shuffled deck. Who wins depends on the session's time of day
(`FIRST_DEALER_TIME_OF_DAY`, pinned = `"day"`, the engine default when not told otherwise):
night favors the earliest month (January) and, on a month tie, the lowest-ranked card of that month
(bright > animal > ribbon > junk); day favors the latest month (December) and, on a tie, the
highest-ranked card. Quoting pagat: "If the game is played at night the player who drew the earliest
month and in case of a tie the lowest valued card of that month (bright>animal>ribbon>junk) is the
first dealer. For a daytime game the first dealer is the player who drew the later month or the
higher valued card in case of a tie." After the first hand, both sources agree the **winner deals
the next hand**; nagari is the pinned exception (section 11): the same dealer redeals. Both rules
live above a single `GoStopEngine` hand, so neither is inside the engine package itself:
`engine/dealing.py:choose_first_dealer` picks the dealer for a sitting's first hand,
`engine/dealing.py:choose_next_dealer` picks every one after it, and `api/session_manager.py`'s
`Session.next_hand()` is what calls the latter and carries the running rng and match score forward
when the web app's "Next hand" button is used, instead of starting an unrelated fresh hand. "Dealer"
never means an actual dealing action here (see the docstring on `choose_next_dealer`) -- the engine
always does the dealing; it's only ever a turn-order label.

## 3. Turn structure

Each turn: play one hand card -> resolve its capture -> draw one card from the deck -> resolve its
capture -> (if applicable) offer GO_STOP decision -> pass turn. A bomb declaration replaces "play
one hand card" but the forced deck-draw-and-resolve step still happens afterward.

## 4. Capture resolution (`capture.py`)

- Played/drawn card matches **0** field cards of its month -> card is added to the field.
- Matches **exactly 1** field card -> capture both (they move to the player's captured pile).
- Matches **2** field cards (can only happen when the initial deal happened to place 2 cards of
  the same month on the field, since normal play/draw resolution never leaves 2 unstacked
  same-month cards sitting on the field) -> capture all 3, and watch the following draw for
  ttadak (section 6).
- Matches **3** field cards -> capture all 4 (this is the "sweep" completion of a bomb/ppeok pile).
- **Sweep bonus (`SWEEP_BONUS_PI`, pinned = 1):** if a single capture empties the field entirely,
  each opponent pays the capturing player 1 pi as a bonus.

## 5. Ppeok (뻑) — `PPEOK_RULESET = "LOCK_AND_PENALTY"`

Sequence: your **hand card** captures exactly one field card of month X (a normal 1-1 pair) — but
then your immediately-following **forced deck draw** is *also* month X. Because a bare 3-card pile
of the same month can't be resolved as a capture (no 4th card yet), none of the 3 cards are taken;
they stay stacked together on the field as a single tagged "ppeok pile." Each opponent immediately
pays the player who created the ppeok 1 pi as a penalty (`PPEOK_PENALTY_PI = 1`). The pile can only
be captured later by whoever plays or draws the 4th card of month X (which then also triggers the
sweep-completion capture-all-4 case above). Pinned explicitly because casual rule explanations
disagree on exact sequencing — this is the mechanical definition both pagat and gostopguide
independently converge on when read carefully.

## 6. Ttadak (따닥) — `TTADAK_BONUS_MODE = "SAME_TURN_DOUBLE_CAPTURE"`

Your hand card captures 2 field cards of the same month in one move, **and** the subsequent forced
deck draw is also that month (completing capture of the 4th card in the *same turn*). This
back-to-back double-capture is ttadak. Bonus: each opponent pays the capturing player 1 pi
(`TTADAK_PENALTY_PI = 1`).

## 7. Bomb (폭탄) — `BOMB_MODE = "THREE_IN_HAND_PLUS_FIELD"`

At the start of your turn, if you hold 3 hand cards of month X and the field has the 4th card of
month X, you may declare a bomb instead of a normal play: reveal and discard all 3 hand cards at
once, capturing all 4 cards of month X immediately. Each opponent pays 1 pi
(`BOMB_PENALTY_PI = 1`). The turn still proceeds to the normal forced-draw step afterward.

**Hand-desync consequence, pinned as `BOMB_HAND_EMPTY_COMPENSATION = "AUTO_DRAW_ONLY"`:** a bomb
consumes 3 hand cards in one turn instead of 1, so a bomber's hand can empty before their
opponent's. Pagat's literal rule ("in any two subsequent turns you may play no card and simply
turn up the top of the stock") credits exactly 2 compensating flip-only turns per bomb. v1 uses a
simpler equivalent: whenever it becomes a player's turn and their hand is already empty, they
automatically just resolve the forced deck draw (no hand card to play, no bomb check) and the turn
proceeds normally otherwise. Net effect on outcomes is the same -- the player keeps participating
in draws/captures every turn until the hand ends -- without needing separate credit bookkeeping.

## 8. Scoring categories (`scoring.py`)

- **Gwang:** 5 = 15 pts. 4 = 4 pts (regardless of whether rain is among them). 3 excluding rain =
  3 pts. 3 including rain = 2 pts (`RAIN_GWANG_PENALTY = 1`, applied only to the 3-gwang case).
  Fewer than 3 = 0.
- **Animal:** >=5 -> 1 pt, +1 per extra beyond 5.
- **Ribbon:** >=5 -> 1 pt, +1 per extra beyond 5. Plus a flat +3 for each complete color set
  (hongdan / chodan / cheongdan) fully held, independent of the count-based score.
- **Godori:** flat +5 if all 3 godori birds are held, independent of/additive with animal-count
  score.
- **Pi:** count with ssangpi = 2. >=10 -> 1 pt, +1 per extra beyond 10.
- A hand only "scores" (can be stopped on) once total points >= `GO_STOP_MIN_SCORE = 7`.

## 9. Multiplier penalties (applied to the winner's final payment from each opponent)

- **Gwang-bak** (`GWANG_BAK_THRESHOLD = 0`): winner scored via gwang, opponent holds 0 gwang ->
  opponent's payment doubles.
- **Pi-bak** (`PI_BAK_THRESHOLD = 5`): opponent holds fewer than 5 pi (ssangpi counted as 2) ->
  doubles. (Noted variant: some casual sources use <7 instead of <5 — kept as an explicit alternate
  config value, not the default.)
- **Meong-bak / animal-bak** (`MEONG_BAK_THRESHOLD = 7`): winner holds 7+ animal cards -> opponent's
  payment doubles.
- Multiple -baks stack multiplicatively.

## 10. Go / Stop

- `GO_STOP_MIN_SCORE = 7` (pinned for both 2- and 3-player v1; some casual 3-player rules use 3 —
  kept as an alternate config value, not default).
- Calling **Stop** immediately ends the hand and banks the current score at the current
  multiplier.
- Calling **Go** continues the hand. `GO_BONUS_POINTS = 1` flat point is added to the eventual
  final score per go called. Starting from the 3rd go, the final score is additionally doubled per
  go beyond the 2nd (`GO_MULTIPLIER_START = 3`, multiplier = `2 ** max(0, go_count - 2)`).
- **Gobak** (`GOBAK_ENABLED = True`, `GOBAK_MULTIPLIER = 2`): if a player calls Go and the *other*
  player ends up winning the hand instead, the go-caller's liability doubles.

## 11. Nagari (나가리) and hand-end-by-exhaustion

A hand ends once every player's hand is empty (not necessarily when the deck is empty too --
2-player deal sizes leave 2 undrawn deck cards even if play runs all the way, since deck and total
hand-card counts don't have to divide evenly). At that point, whoever last qualified
(score >= `GO_STOP_MIN_SCORE`) with the highest score wins as if they'd stopped. If nobody ever
qualified, the hand is void: no
payment changes hands, the same dealer redeals, and next hand's stakes double
(`NAGARI_STAKE_MULTIPLIER = 2`). The same-dealer-redeals half of this is implemented
(`api/session_manager.py`'s `Session.next_hand()`, see section 2a); the stakes-double half is not
yet consumed anywhere -- `NAGARI_STAKE_MULTIPLIER` is defined but nothing multiplies by it, since
this project has no real-money or chip stake to double in the first place. Not inside a single RL
training episode either way.

## 12. Explicitly deferred to a config flag, not implemented in v1

- `HEUNDEUL_ENABLED = False` — declaring "shake" (3 hand cards of one month held at the start of a
  hand) to double the eventual score. Real mechanic, real complexity, not required for the core
  deliverable.
- 3-player-specific go-bak variant (paying for a third player's losses) — engine is 3-player-dealing
  capable (Section 2) but 3-player go/stop settlement is a stretch-phase concern, not v1.
- `NUM_BONUS_CARDS = 0` — bonus/joker cards (보너스패, sometimes themed, e.g. 도깨비 decks), which many
  printed Korean hwatu decks add on top of the standard 48. **Engine, dealing, and scoring support
  are implemented and tested** (`engine/cards.py`, `engine/dealing.py`, `engine/capture.py`,
  `engine/scoring.py`, `engine/engine.py`, `tests/test_bonus_cards.py`); the constant stays `0` by
  default only because of the serving-layer gap in the last bullet below, not because the rule itself
  is unbuilt. Mechanic pinned per [Wikipedia, Go-Stop](https://en.wikipedia.org/wiki/Go-Stop), quoted
  verbatim since it's the one source that states it precisely (pagat.com and gostopguide describe a
  similar but not identical joker rule; this project follows Wikipedia where they differ), confirmed
  against the physical deck in play where Wikipedia is silent:
  - *On the table at the initial deal*: "the dealer collects the bonus card and turns the top card of
    the draw pile face-up and places it on the table" — the literal top card, not a blind pick (that's
    the next case). Scores for whichever player ends up holding it (the dealer here) exactly like any
    other captured card; see `engine/dealing.py:_resolve_initial_bonus_cards` (cascades if the
    replacement is itself a bonus card) and `choose_first_dealer`/`choose_next_dealer` above for who
    "the dealer" is in the first place.
  - *Dealt into a player's hand*: "they may add it to their stock pile at the beginning of any turn
    and draw a card from the draw pile to replace it in their hand." Confirmed in conversation: this
    replacement is a blind pick of any card in the stock — chosen by position, not by seeing its
    face, so it's equivalent to a uniform-random draw (`engine/dealing.py:draw_blind_replacement`).
    Auto-resolved at the start of the holder's turn rather than modeled as a real choice — banking it
    is never worse than holding it, so there's no decision to make (`GoStopEngine._resolve_bonus_cards_in_hand`),
    matching how this project already auto-resolves other no-choice situations.
  - *Flipped from the stock mid-turn*: "they will automatically collect it along with any other cards
    matched during that turn" (`engine/capture.py:_resolve_bonus_draw`). The quoted ppeok exception
    ("all four cards... must remain on the table") can't actually arise here: a ppeok requires the
    draw's month to match the pending pair's, and a bonus card has no month, so it can never be that
    fourth card. What the implementation does instead, which is the sensible reading of the same
    situation: the pending pair resolves as an ordinary non-matching draw (a normal 2-card capture),
    and the bonus card is collected separately on top of that.
  - A bonus card is never placed in the field for matching — it has no month — and contributes 2 to
    the pi-count score once captured (`BONUS_CARD_PI_VALUE = 2`, same as a ssangpi/double-junk card,
    versus 1 for an ordinary junk card), regardless of which of the three cases above put it there.
    `NUM_BONUS_CARDS` has no fixed limit when enabled; `3` is the pinned default, since real decks
    range from a few to as many as the players agree on. Not to be confused with
    `PlayerState.bonus_pi_received`/`bonus_pi_paid`, an unrelated existing mechanic (sweep/ttadak
    penalty payments, sections 4/6) that happens to share the word "bonus".
  - Why `NUM_BONUS_CARDS` still defaults to `0`: turning it on is more than the engine change above.
    `rl/action_space.py`'s `Discrete(51)` reserves ids 48-50 for SKIP/GO/STOP — harmless in practice
    since a bonus card is never offered as a PLAY_CARD or BOMB_DECISION option (it's always resolved
    out of a hand before either decision is reached), but untested at the action-space level. More
    concretely broken: `rl/search.py`'s `determinize` and `rl/obs_encoding.py`'s multi-hot vectors
    both hardcode `range(48)`/width 48 for "every card not yet seen", so the currently-served search
    bot and the RL observation encoder would both undercount or crash the moment a bonus card is
    anywhere but a capture pile. And regardless of any of that, every existing checkpoint under
    `checkpoints*/` was trained on a 48-card game, so enabling this for the network-based bot means
    retraining, not just a config flip.
