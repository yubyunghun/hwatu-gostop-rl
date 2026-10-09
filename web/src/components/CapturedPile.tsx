import { useCardMeta } from "../state/CardMetaContext";
import type { Category } from "../types";
import { Card } from "./Card";

interface CapturedPileProps {
  cardIds: number[];
  score: number;
}

const CATEGORY_ORDER: Category[] = ["gwang", "animal", "ribbon", "junk", "bonus"];

export function CapturedPile({ cardIds, score }: CapturedPileProps) {
  const meta = useCardMeta();
  const counts: Record<Category, number> = { gwang: 0, animal: 0, ribbon: 0, junk: 0, bonus: 0 };
  const byCategory: Record<Category, number[]> = { gwang: [], animal: [], ribbon: [], junk: [], bonus: [] };
  for (const id of cardIds) {
    const cat = meta.get(id)?.category;
    if (cat) {
      counts[cat]++;
      byCategory[cat].push(id);
    }
  }
  return (
    <div className="captured-pile">
      <div className="captured-pile__counts">
        <span className="count count--gwang">광 {counts.gwang}</span>
        <span className="count count--animal">동 {counts.animal}</span>
        <span className="count count--ribbon">띠 {counts.ribbon}</span>
        <span className="count count--junk">피 {counts.junk}</span>
        {counts.bonus > 0 && <span className="count count--bonus">보너스 {counts.bonus}</span>}
      </div>
      <div className="captured-pile__score">score: {score}</div>
      <div className="captured-pile__cards">
        {CATEGORY_ORDER.flatMap((cat) => byCategory[cat]).map((id) => (
          <Card key={id} id={id} selectable={false} />
        ))}
        {cardIds.length === 0 && <div className="captured-pile__empty">no captures yet</div>}
      </div>
    </div>
  );
}
