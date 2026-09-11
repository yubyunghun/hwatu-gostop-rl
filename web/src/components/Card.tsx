import { useCardMeta } from "../state/CardMetaContext";
import type { Category } from "../types";

const CATEGORY_LABEL: Record<Category, string> = {
  gwang: "광",
  animal: "동",
  ribbon: "띠",
  junk: "피",
};

interface CardProps {
  id: number;
  selectable?: boolean;
  selected?: boolean;
  onClick?: (id: number) => void;
}

export function Card({ id, selectable, selected, onClick }: CardProps) {
  const meta = useCardMeta().get(id);
  if (!meta) return null;

  const hue = ((meta.month - 1) * 29) % 360;
  const style = {
    "--card-hue": hue,
  } as React.CSSProperties;

  return (
    <button
      type="button"
      className={`card card--${meta.category}${selectable ? " card--selectable" : ""}${selected ? " card--selected" : ""}`}
      style={style}
      disabled={!selectable}
      onClick={() => onClick?.(id)}
      title={`${meta.month}월 ${meta.name}`}
    >
      <span className="card__month">{meta.month}</span>
      <span className="card__badge">{CATEGORY_LABEL[meta.category]}</span>
      <span className="card__name">{meta.name.replace(/_/g, " ")}</span>
    </button>
  );
}

export function CardBack() {
  return <div className="card card--back" />;
}
