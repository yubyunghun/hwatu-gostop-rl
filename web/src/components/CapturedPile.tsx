import { useCardMeta } from "../state/CardMetaContext";
import type { Category } from "../types";

interface CapturedPileProps {
  cardIds: number[];
  score: number;
}

export function CapturedPile({ cardIds, score }: CapturedPileProps) {
  const meta = useCardMeta();
  const counts: Record<Category, number> = { gwang: 0, animal: 0, ribbon: 0, junk: 0 };
  for (const id of cardIds) {
    const cat = meta.get(id)?.category;
    if (cat) counts[cat]++;
  }
  return (
    <div className="captured-pile">
      <div className="captured-pile__counts">
        <span className="count count--gwang">광 {counts.gwang}</span>
        <span className="count count--animal">동 {counts.animal}</span>
        <span className="count count--ribbon">띠 {counts.ribbon}</span>
        <span className="count count--junk">피 {counts.junk}</span>
      </div>
      <div className="captured-pile__score">score: {score}</div>
    </div>
  );
}
