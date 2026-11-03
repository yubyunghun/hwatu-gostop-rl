import { AnimatePresence } from "motion/react";
import { Card } from "./Card";

interface DeckProps {
  count: number;
  /** The id of whatever card is mid-flight out of the deck right now (see useGameSession's replay),
   * shown face-down here until the frame where it lands reveals it for real. */
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
              <Card id={inTransitCardId} selectable={false} faceDown />
            </div>
          )}
        </AnimatePresence>
      </div>
      <div className="deck__count">{count} left</div>
    </div>
  );
}
