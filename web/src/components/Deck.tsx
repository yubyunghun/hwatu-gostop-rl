import { AnimatePresence } from "motion/react";
import { Card } from "./Card";

interface DeckProps {
  count: number;
  /** The id of whatever card is mid-flight out of the deck right now (see useGameSession's replay).
   * Shown face-up and flashing here, the same as a real draw flips the top card for everyone to see
   * the instant it comes off the deck -- not hidden until it lands. */
  inTransitCardId?: number | null;
}

export function Deck({ count, inTransitCardId }: DeckProps) {
  const stackSize = Math.min(count, 5);

  return (
    <div className="deck">
      <div className="deck__stack">
        {stackSize === 0 && inTransitCardId == null ? (
          <div className="deck__empty">empty</div>
        ) : (
          Array.from({ length: stackSize }, (_, i) => (
            <div className="deck__card" key={i} style={{ "--i": i } as React.CSSProperties} />
          ))
        )}
        <AnimatePresence>
          {inTransitCardId != null && (
            <div className="deck__transit">
              <Card id={inTransitCardId} selectable={false} flash />
            </div>
          )}
        </AnimatePresence>
      </div>
      <div className="deck__count">{count} left</div>
    </div>
  );
}
