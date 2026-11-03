import { useEffect, useRef, useState } from "react";
import type { EventOut } from "../types";

// Event types that move cards into a captured pile (or lock them on the field, for ppeok) -- the
// moments worth calling out visually. FIELD_ADD/GO/STOP/etc. aren't "a card was taken".
const CAPTURE_LIKE = new Set(["CAPTURE", "SWEEP", "BOMB", "PPEOK_LOCK"]);
const FLASH_MS = 1300;

/** Which card ids should currently be pulsing, so it's obvious what was just taken. Compares the
 * incoming event log against the last one it saw (GameStateOut.recent_events is a sliding window of
 * the last few, not a diff) and flashes whatever capture-like event is now newest. */
export function useCaptureFlash(recentEvents: EventOut[]): Set<number> {
  const [flashing, setFlashing] = useState<Set<number>>(new Set());
  const lastSeenKey = useRef<string | null>(null);

  useEffect(() => {
    const latest = recentEvents[recentEvents.length - 1];
    if (!latest) return;
    const key = `${latest.type}:${latest.card_ids.join(",")}:${recentEvents.length}`;
    if (key === lastSeenKey.current) return;
    lastSeenKey.current = key;
    if (!CAPTURE_LIKE.has(latest.type) || latest.card_ids.length === 0) return;

    setFlashing(new Set(latest.card_ids));
    const timer = setTimeout(() => setFlashing(new Set()), FLASH_MS);
    return () => clearTimeout(timer);
  }, [recentEvents]);

  return flashing;
}
