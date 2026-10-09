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

Either resolution step ("resolve its capture") can itself pause the turn for a CAPTURE_CHOICE
decision (section 4) if the card in question matches 2 same-month field cards -- in principle both
steps could pause in the same turn, once each, since the hand-play and the draw land on
independent months. `GoStopEngine` resumes exactly where it left off once the choice is answered
(`choose_capture`), rather than re-running anything.

## 4. Capture resolution (`capture.py`)

- Played/drawn card matches **0** field cards of its month -> card is added to the field.
- Matches **exactly 1** field card -> capture both (they move to the player's captured pile) --
  though not immediately; see the deferred/`pending_pair` note below.
- Matches **exactly 2** field cards -> a real decision, `DecisionNode.CAPTURE_CHOICE`: the player
  chooses which of the two to pair with. Quoting pagat: "If there are two cards of this month in
  the layout, you can choose on which one you will place your played card." The unchosen one is
  simply left on the field -- the rules don't say it goes anywhere, so `resolve_capture_choice`
  doesn't move it. This can happen on either half of a turn, since a played *or* a drawn card is
  just as much "a single card being placed against the layout" either way:
  - From the hand-play: the chosen pair defers exactly like the 1-match case below, because the
    forced draw that follows still needs checking for a ppeok or a bigger sweep.
  - From the forced draw itself: there's no further draw left this turn to defer to, so the chosen
    pair captures immediately.

  **Correction, 2026-10:** earlier versions of this project captured all 3 immediately with no
  choice, sourced (without realizing the two disagreed) from gostopguide's version of this rule
  rather than pagat's. A user who's actually played the game caught it. Every trained model and
  every published result up to that point was produced against the wrong version -- see the
  Corrections section of the README.
- Matches **3** field cards -> capture all 4 (this is the "sweep" completion of a bomb/ppeok pile,
  or of a CAPTURE_CHOICE pair whose field pair's month gets drawn right after -- see section 5).
- **Deferred pairs (`pending_pair`):** a hand-play or draw that matches exactly 1 field card isn't
  captured the instant it matches -- it's held until the following draw is known, because if that
  draw is *also* the same month, the pair plus the draw lock as a ppeok (section 5) instead of
  being captured. A CAPTURE_CHOICE that came from the hand-play becomes a pending pair the same
  way once answered, for the same reason; the field literally has 3 cards of that month sitting
  together at that point (both original candidates plus the played card), which is how
  `resolve_draw` tells "this would be a 3-card ppeok" apart from "this is actually a 4-card sweep,
  because it already started from 3, not 1."
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

This is specifically the **1-match** pending pair reaching a 3rd card. A pending pair that came
from a CAPTURE_CHOICE (section 4) already started from 3 cards on the field, so its own matching
draw makes 4, not 3 -- that's a straight capture, not a ppeok. Pagat states this case explicitly:
"If your played card matched two layout cards and the stock card is also that month, you capture
all four cards of this month."

## 6. Ttadak (따닥) — retired

Earlier versions of this project had a ttadak bonus: a hand-play matching 2 field cards would
capture all 3 immediately, and if the following draw was also that month, capturing the 4th too
counted as "ttadak" and paid a bonus. That was gostopguide's version of the 2-field-card-match
rule (section 4) -- the version this project no longer follows, since it conflicts with pagat's
"you choose which one to pair with," which a user who's actually played the game confirmed is the
one they expect. Once a hand card matching 2 field cards stopped auto-capturing all 3, there was
nothing left for ttadak's trigger condition to fire on, so it was removed rather than built on a
reinterpreted definition that no source actually states. `TTADAK_BONUS_MODE`,
`TTADAK_PENALTY_PI`, `EventType.TTADAK`, and `GameState.ttadak_watch_month` no longer exist.

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
    `PlayerState.bonus_pi_received`/`bonus_pi_paid`, an unrelated existing mechanic (sweep/ppeok
    penalty payments, sections 4/5) that happens to share the word "bonus".
  - **The served search bot and the rules engine fully support bonus cards**, verified by actually
    playing games with them through the real FastAPI app (`TestClient` against `api.main.app`, not
    just unit-level patches). `rl/action_space.py`'s SKIP/GO/STOP now sit at `NUM_CARDS`,
    `NUM_CARDS + 1`, `NUM_CARDS + 2` (derived from `engine.cards.NUM_CARDS`) rather than hardcoded
    48/49/50, so a growing card registry can never collide a real card id with one of them;
    `rl/search.py`'s `determinize` and `rl/obs_encoding.py`'s multi-hot vectors size themselves off
    the same `NUM_CARDS` instead of a hardcoded 48. All of this is a no-op at the default
    `NUM_BONUS_CARDS = 0` (same 48/51 sizes as always, byte-identical to before this was made
    dynamic), so no existing checkpoint under `checkpoints*/` is affected unless bonus cards are
    actually turned on -- and turning them on only matters for the network-based bot
    (`rl/obs_encoding.py`), which isn't what's served; `api/deps.py` serves the search bot, which
    never touches the observation encoder at all.
  - **To actually play with bonus cards**, set `HWATU_NUM_BONUS_CARDS` (e.g. `3`) before starting the
    server: `HWATU_NUM_BONUS_CARDS=3 uvicorn api.main:app --port 8000`. This is an env var, not a
    permanent change to `NUM_BONUS_CARDS`'s default, specifically so the training/eval scripts and
    the test suite keep running against the standard 48-card game unless someone deliberately opts
    in for that process. `NUM_BONUS_CARDS` sizes the global card registry (`engine/cards.py:CARDS`)
    once at import, like every other `rules_config` constant -- it is not a per-request or per-game
    parameter, so don't expect two sessions in the same running server to differ on this.
  - **Three real bugs were caught by actually running a bonus-card game end to end** (through
    `TestClient` against the live app, not just unit tests against patched state) that no amount of
    reasoning about the code would have caught by inspection alone:
    1. `choose_first_dealer`'s draw could pull a bonus card and crash looking up its category rank
       (a bonus card has none) -- fixed by excluding bonus cards from that draw's candidate pool
       (nothing describes using one for this, and the natural reading is that only the real 48 ever
       take part).
    2. `GoStopEngine._resolve_bonus_cards_in_hand` only scanned a player's hand once, so a blind
       replacement draw that was itself a bonus card got added to the hand but never resolved,
       surfacing later as an illegal PLAY_CARD option -- fixed by looping until no bonus card remains
       in the hand, mirroring the cascade already handled in `_resolve_initial_bonus_cards`.
    3. Unrelated to bonus cards, but found while writing a fresh end-to-end smoke test: the existing
       API tests' `BOMB_DECISION` handling called `month_of()` on a value that was already a month
       (`GoStopEngine.legal_options()` returns bomb-able months directly, not card ids), which is
       simply wrong -- it happened to never be caught because none of the suite's fixed seeds had
       exercised that branch meaningfully before. Fixed in `tests/test_api.py`, with a new test that
       forces a `BOMB_DECISION` directly rather than hoping a seed produces one.
