import { AnimatePresence, motion } from "motion/react";
import { useCardMeta } from "../state/CardMetaContext";
import type { Category } from "../types";
import { Card, CardBack } from "./Card";

interface HandProps {
  cardIds: number[] | null;
  hiddenCount: number;
  selectable: boolean;
  onPlay?: (id: number) => void;
}

const CATEGORY_ORDER: Category[] = ["gwang", "animal", "ribbon", "junk", "bonus"];

export function Hand({ cardIds, hiddenCount, selectable, onPlay }: HandProps) {
  const meta = useCardMeta();

  if (cardIds === null) {
    // Hidden hand (the opponent's) -- nothing to group by, we can't see what's in it.
    return (
      <div className="hand hand--hidden">
        <AnimatePresence mode="popLayout">
          {Array.from({ length: hiddenCount }, (_, i) => (
            <CardBack key={i} />
          ))}
        </AnimatePresence>
      </div>
    );
  }

  const byCategory: Record<Category, number[]> = { gwang: [], animal: [], ribbon: [], junk: [], bonus: [] };
  for (const id of cardIds) {
    const cat = meta.get(id)?.category;
    if (cat) byCategory[cat].push(id);
  }

  return (
    <div className="hand">
      <AnimatePresence mode="popLayout">
        {CATEGORY_ORDER.filter((cat) => byCategory[cat].length > 0).map((cat) => (
          <motion.div className="hand__group" key={cat} layout>
            <AnimatePresence mode="popLayout">
              {byCategory[cat].map((id) => (
                <Card key={id} id={id} selectable={selectable} onClick={onPlay} />
              ))}
            </AnimatePresence>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
