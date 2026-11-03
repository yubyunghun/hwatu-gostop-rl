import { useCallback, useRef, useState } from "react";
import { createSession, nextHand as apiNextHand, submitAction as apiSubmitAction } from "../api/client";
import type { ActionRequest, GameStateOut } from "../types";

// How long each replayed frame stays on screen, and how long a drawn card pauses face-down at the
// deck before its frame reveals it -- see playSteps below.
const STEP_DELAY_MS = 650;
const DRAW_TRANSIT_MS = 320;

const sleep = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));

function stripSteps(s: GameStateOut): GameStateOut {
  return { ...s, steps: [] };
}

/** A step is a "hand_play" if some player's hand_count dropped (a card left their hand onto the
 * field), a "draw" if the deck_count dropped instead (nothing moved out of either hand), or "other"
 * for a pure reshuffle with no count change (e.g. a capture-choice resolution). These two counts are
 * always public, even for the opponent's hidden hand, so this needs no event parsing. */
function classifyStep(prev: GameStateOut, next: GameStateOut): "hand_play" | "draw" | "other" {
  const handShrank = next.players.some((p, i) => prev.players[i].hand_count - p.hand_count > 0);
  if (handShrank) return "hand_play";
  if (prev.deck_count > next.deck_count) return "draw";
  return "other";
}

/** The card id(s) that appeared somewhere visible (field or either captured pile) in `next` but were
 * nowhere visible in `prev` -- for a "draw" step this is exactly the card that came off the deck,
 * since every other id involved was already sitting on the field beforehand. */
function newlyVisibleIds(prev: GameStateOut, next: GameStateOut): number[] {
  const known = new Set<number>([...prev.field, ...prev.players.flatMap((p) => p.captured)]);
  for (const p of prev.players) {
    if (p.hand) for (const id of p.hand) known.add(id);
  }
  const candidates = new Set<number>([...next.field, ...next.players.flatMap((p) => p.captured)]);
  return [...candidates].filter((id) => !known.has(id));
}

export function useGameSession() {
  const [state, setState] = useState<GameStateOut | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [transitCardId, setTransitCardId] = useState<number | null>(null);
  // Guards against a stale replay still writing frames after a newer action superseded it.
  const replayToken = useRef(0);

  const playSteps = useCallback(async (from: GameStateOut, response: GameStateOut) => {
    const token = ++replayToken.current;
    const frames = [...response.steps.map(stripSteps), stripSteps(response)];
    let prev = from;
    for (const frame of frames) {
      if (replayToken.current !== token) return;
      if (classifyStep(prev, frame) === "draw") {
        const [drawnId] = newlyVisibleIds(prev, frame);
        if (drawnId !== undefined) {
          setTransitCardId(drawnId);
          await sleep(DRAW_TRANSIT_MS);
          if (replayToken.current !== token) return;
        }
      }
      setTransitCardId(null);
      setState(frame);
      prev = frame;
      await sleep(STEP_DELAY_MS);
    }
  }, []);

  const start = useCallback(async (humanSeat: number, seed?: number) => {
    setBusy(true);
    setError(null);
    try {
      const response = await createSession(humanSeat, seed);
      setState(stripSteps(response)); // the initial deal itself isn't replayed, just shown directly
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }, []);

  const act = useCallback(
    async (action: ActionRequest) => {
      if (!state) return;
      setBusy(true);
      setError(null);
      try {
        const response = await apiSubmitAction(state.session_id, action);
        await playSteps(state, response);
      } catch (e) {
        setError(String(e));
      } finally {
        setBusy(false);
      }
    },
    [state, playSteps],
  );

  const nextHand = useCallback(async () => {
    if (!state) return;
    setBusy(true);
    setError(null);
    try {
      const response = await apiNextHand(state.session_id);
      await playSteps(state, response);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }, [state, playSteps]);

  return { state, busy, error, start, act, nextHand, transitCardId };
}
