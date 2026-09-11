import { Card, CardBack } from "./Card";

interface HandProps {
  cardIds: number[] | null;
  hiddenCount: number;
  selectable: boolean;
  onPlay?: (id: number) => void;
}

export function Hand({ cardIds, hiddenCount, selectable, onPlay }: HandProps) {
  if (cardIds === null) {
    return (
      <div className="hand hand--hidden">
        {Array.from({ length: hiddenCount }, (_, i) => (
          <CardBack key={i} />
        ))}
      </div>
    );
  }
  return (
    <div className="hand">
      {cardIds.map((id) => (
        <Card key={id} id={id} selectable={selectable} onClick={onPlay} />
      ))}
    </div>
  );
}
