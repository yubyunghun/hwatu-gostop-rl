interface GoStopPromptProps {
  onGo: () => void;
  onStop: () => void;
  busy: boolean;
}

export function GoStopPrompt({ onGo, onStop, busy }: GoStopPromptProps) {
  return (
    <div className="prompt prompt--go-stop">
      <p>You've reached the scoring threshold. Go for more points, or stop and bank the score?</p>
      <div className="prompt__actions">
        <button type="button" disabled={busy} onClick={onGo}>Go</button>
        <button type="button" disabled={busy} onClick={onStop}>Stop</button>
      </div>
    </div>
  );
}
