import { Card } from "./Card";

interface CaptureChoicePromptProps {
  legalOptions: (number | string)[];
  onChoose: (cardId: number) => void;
  busy: boolean;
}

export function CaptureChoicePrompt({ legalOptions, onChoose, busy }: CaptureChoicePromptProps) {
  // Always exactly 2 real field card ids -- see GoStopEngine.legal_options() for CAPTURE_CHOICE.
  const candidates = legalOptions.filter((o): o is number => typeof o === "number");

  return (
    <div className="prompt prompt--capture-choice">
      <p>That matches 2 cards on the field -- which one do you want to pair it with?</p>
      <div className="prompt__actions">
        {candidates.map((id) => (
          <Card key={id} id={id} selectable={!busy} onClick={onChoose} />
        ))}
      </div>
    </div>
  );
}
