"""What does each model actually *do*? Win rates say how well a policy plays, not whether its
individual decisions are sensible. This plays a model against the heuristic and logs, at every
decision the model makes, the properties a human would judge it on:

- card play: when a capture was available did it take one? the most valuable one? when nothing
  could be captured, did it discard its least valuable card?
- bombs: did it declare when it could?
- go/stop: how often does it press on, and at what score / how late in the hand?
- agreement with the heuristic overall, plus a sample of concrete disagreements to read.
"""

import argparse
import json
import random
import sys
from pathlib import Path

import numpy as np

from engine.cards import card, month_of
from engine.engine import GoStopEngine
from engine.go_stop import current_raw_score
from engine.state import DecisionNode
from rl.action_space import GO, SKIP, apply_action, legal_action_mask
from rl.baselines.heuristic_agent import _card_value, heuristic_policy
from rl.evaluate import HELDOUT_EVAL_SEED, episode_setup
from rl.final_eval import checkpoints_for
from rl.model_agent import make_model_policy

PROJECT_ROOT = Path(__file__).resolve().parent.parent

MODELS = {
    "heuristic (reference)": None,
    "cloned heuristic (BC)": "checkpoints_bc/bc_model.zip",
    "BC + PPO fine-tune": "checkpoints_finetune",
    "PPO from scratch (shaping)": "checkpoints_reward_shaping",
}


def describe(card_id: int) -> str:
    c = card(card_id)
    return f"{c.month}-{c.category.value}-{c.name}"


def _capture_options(s, me: int) -> dict[int, int | None]:
    """card id -> total value captured by playing it, or None if it would only be discarded."""
    out = {}
    for cid in s.players[me].hand:
        pile = s.field.get(month_of(cid), [])
        out[cid] = sum(_card_value(x) for x in pile + [cid]) if pile else None
    return out


def analyze(policy, games: int, seed: int, example_slots: int = 10) -> dict:
    rng = random.Random(seed)
    c = dict.fromkeys([
        "decisions", "agree", "play_n", "play_agree", "play_capture_avail", "play_took_capture",
        "play_best_capture", "play_dump_n", "play_dump_lowest", "bomb_avail", "bomb_declared",
        "gostop_n", "gostop_agree", "go_n", "go_score_sum", "stop_score_sum", "go_deck_sum",
        "stop_deck_sum", "games", "wins", "losses", "go_games", "go_games_won",
    ], 0)
    examples: list[dict] = []
    seen_disagreements = 0

    for g in range(games):
        swapped, dealer = episode_setup(g)
        me = 1 if swapped else 0
        engine = GoStopEngine(num_players=2, dealer=dealer, rng=random.Random(seed + g))
        while not engine.state.hand_over:
            s = engine.state
            legal = np.flatnonzero(legal_action_mask(engine))
            if s.turn == me:
                action = int(policy(engine, legal))
                reference = int(heuristic_policy(engine, legal))
                c["decisions"] += 1
                c["agree"] += int(action == reference)
                decision = s.pending_decision

                if decision == DecisionNode.PLAY_CARD:
                    c["play_n"] += 1
                    c["play_agree"] += int(action == reference)
                    options = _capture_options(s, me)
                    captures = {k: v for k, v in options.items() if v is not None}
                    if captures:
                        c["play_capture_avail"] += 1
                        if action in captures:
                            c["play_took_capture"] += 1
                            c["play_best_capture"] += int(captures[action] == max(captures.values()))
                    else:
                        c["play_dump_n"] += 1
                        lowest = min(_card_value(k) for k in options)
                        c["play_dump_lowest"] += int(_card_value(action) == lowest)
                elif decision == DecisionNode.BOMB_DECISION:
                    c["bomb_avail"] += 1
                    c["bomb_declared"] += int(action != SKIP)
                elif decision == DecisionNode.GO_STOP:
                    c["gostop_n"] += 1
                    c["gostop_agree"] += int(action == reference)
                    score = current_raw_score(s, me).total
                    if action == GO:
                        c["go_n"] += 1
                        c["go_score_sum"] += score
                        c["go_deck_sum"] += len(s.deck)
                    else:
                        c["stop_score_sum"] += score
                        c["stop_deck_sum"] += len(s.deck)

                if action != reference and decision in (DecisionNode.PLAY_CARD, DecisionNode.GO_STOP):
                    seen_disagreements += 1
                    ex = {
                        "decision": decision.name,
                        "hand": [describe(x) for x in sorted(s.players[me].hand)],
                        "field": [describe(x) for x in sorted(s.field_cards())],
                        "model": describe(action) if action < 48 else ("GO" if action == GO else "STOP"),
                        "heuristic": describe(reference) if reference < 48 else ("GO" if reference == GO else "STOP"),
                    }
                    if decision == DecisionNode.PLAY_CARD:
                        opts = _capture_options(s, me)
                        ex["model_captures"] = opts[action] is not None
                        ex["heuristic_captures"] = opts[reference] is not None
                        ex["model_value"] = opts[action]
                        ex["heuristic_value"] = opts[reference]
                    # reservoir sampling so examples are spread across the whole run
                    if len(examples) < example_slots:
                        examples.append(ex)
                    else:
                        j = rng.randrange(seen_disagreements)
                        if j < example_slots:
                            examples[j] = ex
            else:
                action = int(heuristic_policy(engine, legal))
            apply_action(engine, action)

        result = engine.state.result
        c["games"] += 1
        if not result.nagari:
            won = result.winner == me
            c["wins"] += int(won)
            c["losses"] += int(not won)
        if engine.state.players[me].go_count > 0:
            c["go_games"] += 1
            c["go_games_won"] += int((not result.nagari) and result.winner == me)
    return {"counts": c, "examples": examples}


def rates(c: dict) -> dict:
    def ratio(a, b):
        return float(c[a] / c[b]) if c[b] else None

    return {
        "agree_with_heuristic": ratio("agree", "decisions"),
        "play_agree": ratio("play_agree", "play_n"),
        "takes_available_capture": ratio("play_took_capture", "play_capture_avail"),
        "picks_best_capture": ratio("play_best_capture", "play_took_capture"),
        "dumps_lowest_value": ratio("play_dump_lowest", "play_dump_n"),
        "declares_bomb": ratio("bomb_declared", "bomb_avail"),
        "goes_on": ratio("go_n", "gostop_n"),
        "mean_score_when_go": float(c["go_score_sum"] / c["go_n"]) if c["go_n"] else None,
        "mean_score_when_stop": (float(c["stop_score_sum"] / (c["gostop_n"] - c["go_n"]))
                                  if c["gostop_n"] - c["go_n"] else None),
        "go_hands_won": ratio("go_games_won", "go_games"),
        "win_rate_vs_heuristic": ratio("wins", "games"),
        "n_play": c["play_n"], "n_capture_avail": c["play_capture_avail"],
        "n_gostop": c["gostop_n"], "n_bomb_avail": c["bomb_avail"],
    }


def main(games: int, examples_for: str) -> None:
    from sb3_contrib import MaskablePPO

    report, all_examples = {}, {}
    for label, location in MODELS.items():
        if location is None:
            policy = heuristic_policy
        else:
            path = checkpoints_for(PROJECT_ROOT / location, 1)[-1]
            policy = make_model_policy(MaskablePPO.load(str(path)), deterministic=True)
        out = analyze(policy, games, HELDOUT_EVAL_SEED)
        report[label] = rates(out["counts"])
        all_examples[label] = out["examples"]
        print(f"analyzed {label}", flush=True)

    keys = ["agree_with_heuristic", "takes_available_capture", "picks_best_capture",
            "dumps_lowest_value", "declares_bomb", "goes_on", "mean_score_when_go",
            "mean_score_when_stop", "go_hands_won", "win_rate_vs_heuristic"]
    print()
    print("metric".ljust(26) + "".join(m.ljust(28) for m in MODELS))
    for k in keys:
        row = k.ljust(26)
        for label in MODELS:
            v = report[label][k]
            row += (f"{v:.3f}" if v is not None else "n/a").ljust(28)
        print(row)
    print()
    for label in MODELS:
        r = report[label]
        print(f"{label}: {r['n_play']} card plays ({r['n_capture_avail']} with a capture available), "
              f"{r['n_gostop']} go/stop decisions, {r['n_bomb_avail']} bomb chances")

    out_path = PROJECT_ROOT / "checkpoints" / "behavior_analysis.json"
    out_path.write_text(json.dumps({"games": games, "metrics": report, "examples": all_examples},
                                   indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote {out_path.name}")

    print(f"\nSample disagreements with the heuristic -- {examples_for}:")
    for ex in all_examples[examples_for]:
        print(json.dumps(ex, ensure_ascii=False))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--games", type=int, default=300)
    parser.add_argument("--examples-for", type=str, default="BC + PPO fine-tune")
    args = parser.parse_args()
    main(args.games, args.examples_for)
