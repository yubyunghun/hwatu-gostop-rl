import { BombPrompt } from "../components/BombPrompt";
import { CaptureChoicePrompt } from "../components/CaptureChoicePrompt";
import { Deck } from "../components/Deck";
import { Field } from "../components/Field";
import { GameLog } from "../components/GameLog";
import { GoStopPrompt } from "../components/GoStopPrompt";
import { Hand } from "../components/Hand";
import { ScoreBoard } from "../components/ScoreBoard";
import { TurnBanner } from "../components/TurnBanner";
import { useCaptureFlash } from "../state/useCaptureFlash";
import { useGameSession } from "../state/useGameSession";

export function GamePage() {
  const { state, busy, error, start, act, nextHand, transitCardId, turnBanner } = useGameSession();
  // Called unconditionally (rules of hooks) even before `state` exists yet.
  const flashIds = useCaptureFlash(state?.recent_events ?? []);

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
      <ScoreBoard state={state} flashIds={flashIds} />

      <section className="board-area">
        <TurnBanner who={turnBanner} />
        <Hand cardIds={opponent.hand} hiddenCount={opponent.hand_count} selectable={false} />
        <div className="board-area__middle">
          <Field cardIds={state.field} />
          <Deck count={state.deck_count} inTransitCardId={transitCardId} />
        </div>
        <Hand
          cardIds={me.hand}
          hiddenCount={me.hand_count}
          selectable={isMyTurn && state.pending_decision === "PLAY_CARD" && !busy}
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
      {isMyTurn && state.pending_decision === "CAPTURE_CHOICE" && (
        <CaptureChoicePrompt
          legalOptions={state.legal_options}
          busy={busy}
          onChoose={(cardId) => act({ type: "choose_capture", card_id: cardId })}
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
          <p className="match-scores">Match total: {state.match_scores.join(" / ")}</p>
          <button type="button" disabled={busy} onClick={nextHand}>
            Next hand
          </button>
          <button type="button" disabled={busy} onClick={() => start(0)}>
            New match
          </button>
        </div>
      )}

      {error && <p className="error-banner">{error}</p>}
      <GameLog events={state.recent_events} />
    </div>
  );
}
