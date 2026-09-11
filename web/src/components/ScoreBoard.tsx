import type { GameStateOut } from "../types";
import { CapturedPile } from "./CapturedPile";

export function ScoreBoard({ state }: { state: GameStateOut }) {
  return (
    <div className="score-board">
      {state.players.map((p) => (
        <div key={p.seat} className={`score-board__player${p.seat === state.turn ? " score-board__player--active" : ""}`}>
          <div className="score-board__label">
            {p.seat === state.viewer_seat ? "You" : "Opponent"}
            {p.seat === state.turn && !state.hand_over ? " (turn)" : ""}
          </div>
          <CapturedPile cardIds={p.captured} score={p.score} />
          <div className="score-board__go">go x{p.go_count}</div>
        </div>
      ))}
      <div className="score-board__deck">deck: {state.deck_count} cards left</div>
    </div>
  );
}
