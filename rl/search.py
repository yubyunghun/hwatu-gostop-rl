"""Determinized Monte Carlo search (PIMC) layered on top of the heuristic.

Every learned policy so far tops out at "the heuristic, plus a better go/stop rule": neither
imitation nor PPO found better *card play*. Search is the standard way past a hand-written baseline
because it doesn't need a better teacher, it needs a simulator, and the engine is one.

At each decision:
  1. Sample a plausible hidden world: the opponent's hand and the deck order are drawn uniformly
     from the cards nobody has seen (everything not in my hand, the field, or either capture pile).
  2. For every legal action, apply it in a copy of that world and play the rest of the hand out with
     the heuristic on both sides. Record my payoff.
  3. Repeat over many sampled worlds and compare actions.

Two details matter for not making things worse:
- Common random numbers: every action is evaluated in the *same* sampled worlds, so what's compared
  is a paired difference, which is far less noisy than comparing independent averages.
- Cautious deviation: search only overrides the heuristic's action when some other action beats it
  by at least `min_z` standard errors of that paired difference. Otherwise the heuristic's move is
  kept, so noise alone can't drag play below the base policy.

Limitations, stated up front: worlds are sampled uniformly (no inference from what the opponent has
or hasn't played), and rollouts assume both sides continue with the heuristic.
"""

import copy
import math
import random

import numpy as np

from engine.engine import GoStopEngine
from engine.state import DecisionNode
from rl.action_space import apply_action, legal_action_mask
from rl.baselines.heuristic_agent import heuristic_policy

MAX_ROLLOUT_STEPS = 500

# Which decision nodes search is allowed to override the base policy on. Restricting it isolates
# where any gain comes from: better card play, or just a better go/stop rule.
SEARCHED_NODES = {
    "all": {DecisionNode.PLAY_CARD, DecisionNode.BOMB_DECISION, DecisionNode.GO_STOP},
    "play": {DecisionNode.PLAY_CARD},
    "gostop": {DecisionNode.GO_STOP},
}


def determinize(engine: GoStopEngine, me: int, rng: random.Random) -> GoStopEngine:
    """A copy of the game with the hidden cards re-dealt at random, consistent with what `me` can see.

    The opponent keeps the same number of cards; the rest of the unseen cards become the deck in a
    random order. Only public information and `me`'s own hand are used to build it."""
    s = engine.state
    opp = s.opponents(me)[0]
    known = set(s.players[me].hand) | set(s.field_cards())
    known |= set(s.players[me].captured) | set(s.players[opp].captured)
    unseen = [c for c in range(48) if c not in known]
    rng.shuffle(unseen)
    k = len(s.players[opp].hand)

    world = copy.deepcopy(engine)
    world.state.players[opp].hand = set(unseen[:k])
    world.state.deck = unseen[k:]
    world.state.events = []
    return world


def play_out(engine: GoStopEngine, policy=heuristic_policy) -> None:
    steps = 0
    while not engine.state.hand_over:
        steps += 1
        if steps > MAX_ROLLOUT_STEPS:
            raise RuntimeError("rollout did not terminate")
        legal = np.flatnonzero(legal_action_mask(engine))
        apply_action(engine, int(policy(engine, legal)))


def payoff_of(engine: GoStopEngine, me: int) -> float:
    result = engine.state.result
    return 0.0 if result.nagari else float(result.scores[me])


class SearchPolicy:
    """(engine, legal_actions) -> action, like every other policy in rl/."""

    def __init__(self, determinizations: int = 100, min_z: float = 1.0, seed: int = 0,
                 base_policy=heuristic_policy, nodes: str = "all"):
        self.nodes = SEARCHED_NODES[nodes]
        self.determinizations = determinizations
        self.min_z = min_z
        self.base_policy = base_policy
        self._rng = random.Random(seed)
        # bookkeeping: how often search runs at all, and how often it overrides the heuristic
        self.decisions = 0
        self.searched = 0
        self.deviations = 0

    def value_table(self, engine: GoStopEngine, candidates: list[int]) -> np.ndarray:
        """payoffs[d, j]: payoff of candidate j in sampled world d (same worlds for every j)."""
        me = engine.state.turn
        table = np.zeros((self.determinizations, len(candidates)))
        for d in range(self.determinizations):
            world = determinize(engine, me, self._rng)
            for j, action in enumerate(candidates):
                sim = copy.deepcopy(world)
                apply_action(sim, action)
                play_out(sim, self.base_policy)
                table[d, j] = payoff_of(sim, me)
        return table

    def __call__(self, engine: GoStopEngine, legal_actions) -> int:
        candidates = [int(a) for a in legal_actions]
        base = int(self.base_policy(engine, legal_actions))
        self.decisions += 1
        if (len(candidates) == 1 or math.isinf(self.min_z)
                or engine.state.pending_decision not in self.nodes):
            return base
        self.searched += 1

        table = self.value_table(engine, candidates)
        h = candidates.index(base)
        diffs = table - table[:, [h]]
        mean = diffs.mean(axis=0)
        se = diffs.std(axis=0, ddof=1) / math.sqrt(self.determinizations)
        best_action, best_mean = base, 0.0
        for j, action in enumerate(candidates):
            if j == h or mean[j] <= best_mean:
                continue
            z = math.inf if se[j] == 0 else mean[j] / se[j]
            if z >= self.min_z:
                best_action, best_mean = action, float(mean[j])
        self.deviations += int(best_action != base)
        return best_action
