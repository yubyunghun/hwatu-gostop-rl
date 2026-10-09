import { useState } from "react";
import { useCardMeta } from "../state/CardMetaContext";
import type { Category } from "../types";

const CATEGORY_LABEL: Record<Category, string> = {
  gwang: "광",
  animal: "동",
  ribbon: "띠",
  junk: "피",
  bonus: "보너스",
};

interface CardProps {
  id: number;
  selectable?: boolean;
  selected?: boolean;
  onClick?: (id: number) => void;
}

export function Card({ id, selectable, selected, onClick }: CardProps) {
  const meta = useCardMeta().get(id);
  // Real card art, if you've dropped one in web/public/cards/ (see the README there) -- falls back
  // to the plain colored box below for any id that doesn't have one yet.
  const [imageFailed, setImageFailed] = useState(false);
  if (!meta) return null;

  // A bonus card belongs to no month (RULES.md #12); give it a fixed hue instead of month-based one.
  const hue = meta.month === null ? 0 : ((meta.month - 1) * 29) % 360;
  const style = {
    "--card-hue": hue,
  } as React.CSSProperties;
  const title = meta.month === null ? meta.name : `${meta.month}월 ${meta.name}`;
  const className = `card card--${meta.category}${selectable ? " card--selectable" : ""}${selected ? " card--selected" : ""}${imageFailed ? "" : " card--illustrated"}`;

  return (
    <button
      type="button"
      className={className}
      style={style}
      disabled={!selectable}
      onClick={() => onClick?.(id)}
      title={title}
    >
      {!imageFailed && (
        <img
          className="card__art"
          src={`/cards/${id}.png`}
          alt={title}
          draggable={false}
          onError={() => setImageFailed(true)}
        />
      )}
      {imageFailed && (
        <>
          <span className="card__month">{meta.month ?? CATEGORY_LABEL[meta.category]}</span>
          <span className="card__badge">{CATEGORY_LABEL[meta.category]}</span>
          <span className="card__name">{meta.name.replace(/_/g, " ")}</span>
        </>
      )}
    </button>
  );
}

export function CardBack() {
  const [imageFailed, setImageFailed] = useState(false);
  return (
    <div className={`card card--back${imageFailed ? "" : " card--illustrated"}`}>
      {!imageFailed && (
        <img
          className="card__art"
          src="/cards/back.png"
          alt="card back"
          draggable={false}
          onError={() => setImageFailed(true)}
        />
      )}
    </div>
  );
}
