import { useCallback, useState } from "react";
import { createSession, submitAction as apiSubmitAction } from "../api/client";
import type { ActionRequest, GameStateOut } from "../types";

export function useGameSession() {
  const [state, setState] = useState<GameStateOut | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const start = useCallback(async (humanSeat: number, seed?: number) => {
    setBusy(true);
    setError(null);
    try {
      setState(await createSession(humanSeat, seed));
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
        setState(await apiSubmitAction(state.session_id, action));
      } catch (e) {
        setError(String(e));
      } finally {
        setBusy(false);
      }
    },
    [state],
  );

  return { state, busy, error, start, act };
}
