import { AnimatePresence, motion } from "motion/react";
import { useCardMeta } from "../state/CardMetaContext";
import { Card } from "./Card";

interface FieldProps {
  cardIds: number[];
  selectableIds?: Set<number>;
  onSelect?: (id: number) => void;
}

export function Field({ cardIds, selectableIds, onSelect }: FieldProps) {
  const meta = useCardMeta();
  const byMonth = new Map<number, number[]>();
  for (const id of cardIds) {
    const month = meta.get(id)?.month ?? 0;
    byMonth.set(month, [...(byMonth.get(month) ?? []), id]);
  }
  const months = [...byMonth.keys()].sort((a, b) => a - b);

  return (
    <div className="field">
      <AnimatePresence mode="popLayout">
        {months.map((month) => (
          <motion.div className="field__pile" key={month} layout>
            <AnimatePresence mode="popLayout">
              {byMonth.get(month)!.map((id) => (
                <Card
                  key={id}
                  id={id}
                  selectable={selectableIds?.has(id)}
                  selected={false}
                  onClick={onSelect}
                />
              ))}
            </AnimatePresence>
          </motion.div>
        ))}
      </AnimatePresence>
      {cardIds.length === 0 && <div className="field__empty">field is empty</div>}
    </div>
  );
}
