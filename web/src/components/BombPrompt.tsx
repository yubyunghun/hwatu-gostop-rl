interface BombPromptProps {
  legalOptions: (number | string)[];
  onBomb: (month: number) => void;
  onSkip: () => void;
  busy: boolean;
}

export function BombPrompt({ legalOptions, onBomb, onSkip, busy }: BombPromptProps) {
  // legalOptions for a bomb decision are already month numbers (plus "SKIP"), not card ids -- see
  // GoStopEngine.legal_options()/available_bombs(). No card lookup needed, and doing one (treating
  // the month as if it were a card id to look up) is exactly the bug that was here before: it sent
  // whatever month that unrelated card id happened to belong to instead of the real one.
  const bombMonths = legalOptions.filter((o): o is number => typeof o === "number");

  return (
    <div className="prompt prompt--bomb">
      <p>You can declare a bomb!</p>
      <div className="prompt__actions">
        {bombMonths.map((month) => (
          <button type="button" key={month} disabled={busy} onClick={() => onBomb(month)}>
            Bomb month {month}
          </button>
        ))}
        <button type="button" disabled={busy} onClick={onSkip}>Skip</button>
      </div>
    </div>
  );
}
