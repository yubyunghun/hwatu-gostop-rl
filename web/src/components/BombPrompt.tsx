import { useCardMeta } from "../state/CardMetaContext";

interface BombPromptProps {
  legalOptions: (number | string)[];
  onBomb: (month: number) => void;
  onSkip: () => void;
  busy: boolean;
}

export function BombPrompt({ legalOptions, onBomb, onSkip, busy }: BombPromptProps) {
  const meta = useCardMeta();
  const bombCardIds = legalOptions.filter((o): o is number => typeof o === "number");

  return (
    <div className="prompt prompt--bomb">
      <p>You can declare a bomb!</p>
      <div className="prompt__actions">
        {bombCardIds.map((id) => {
          const month = meta.get(id)?.month;
          return (
            <button type="button" key={id} disabled={busy || month === undefined} onClick={() => month !== undefined && onBomb(month)}>
              Bomb month {month}
            </button>
          );
        })}
        <button type="button" disabled={busy} onClick={onSkip}>Skip</button>
      </div>
    </div>
  );
}
