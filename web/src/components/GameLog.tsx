import type { EventOut } from "../types";

const LABEL: Record<string, string> = {
  FIELD_ADD: "placed on field",
  CAPTURE: "captured",
  SWEEP: "swept the field! +pi",
  PPEOK_LOCK: "ppeok! cards locked on field",
  TTADAK: "ttadak! +pi",
  BOMB: "bomb!",
  GO: "called GO",
  STOP: "called STOP",
  NAGARI: "nagari -- deck exhausted, no winner",
  HAND_END: "hand ended",
};

export function GameLog({ events }: { events: EventOut[] }) {
  return (
    <ul className="game-log">
      {events.map((e, i) => (
        <li key={i}>
          {e.player !== null ? `P${e.player}: ` : ""}
          {LABEL[e.type] ?? e.type}
          {e.card_ids.length > 0 ? ` (${e.card_ids.join(", ")})` : ""}
        </li>
      ))}
    </ul>
  );
}
