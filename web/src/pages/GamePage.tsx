import { BombPrompt } from "../components/BombPrompt";
import { Field } from "../components/Field";
import { GameLog } from "../components/GameLog";
import { GoStopPrompt } from "../components/GoStopPrompt";
import { Hand } from "../components/Hand";
import { ScoreBoard } from "../components/ScoreBoard";
import { useGameSession } from "../state/useGameSession";

export function GamePage() {
  const { state, busy, error, start, act } = useGameSession();

  if (!state) {
    return (
      <div className="game-page game-page--start">
        <button type="button" disabled={busy} onClick={() => start(0)}>
          Start new hand
        </button>
        {error && <p className="error-banner">{error}</p>}
      </div>
    );
  }

  const me = state.players[state.viewer_seat];
  const opponent = state.players.find((p) => p.seat !== state.viewer_seat)!;
  const isMyTurn = state.turn === state.viewer_seat && !state.hand_over;

  return (
    <div className="game-page">
      <ScoreBoard state={state} />

      <section className="board-area">
        <Hand cardIds={opponent.hand} hiddenCount={opponent.hand_count} selectable={false} />
        <Field cardIds={state.field} />
        <Hand
          cardIds={me.hand}
          hiddenCount={me.hand_count}
          selectable={isMyTurn && state.pending_decision === "PLAY_CARD"}
          onPlay={(id) => act({ type: "play_card", card_id: id })}
        />
      </section>

      {isMyTurn && state.pending_decision === "BOMB_DECISION" && (
        <BombPrompt
          legalOptions={state.legal_options}
          busy={busy}
          onBomb={(month) => act({ type: "declare_bomb", month })}
          onSkip={() => act({ type: "skip_bomb" })}
        />
      )}
      {isMyTurn && state.pending_decision === "GO_STOP" && (
        <GoStopPrompt busy={busy} onGo={() => act({ type: "go" })} onStop={() => act({ type: "stop" })} />
      )}

      {state.hand_over && state.result && (
        <div className="prompt prompt--result">
          {state.result.nagari ? (
            <p>Nagari -- deck exhausted with no qualifying score. No payment this hand.</p>
          ) : (
            <p>
              {state.result.winner === state.viewer_seat ? "You win!" : "Opponent wins."}{" "}
              Scores: {state.result.scores.join(" / ")}
            </p>
          )}
          <button type="button" disabled={busy} onClick={() => start(0)}>
            Play again
          </button>
        </div>
      )}

      {error && <p className="error-banner">{error}</p>}
      <GameLog events={state.recent_events} />
    </div>
  );
}
