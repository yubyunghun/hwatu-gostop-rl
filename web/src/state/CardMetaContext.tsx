import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { fetchCards } from "../api/client";
import type { CardMeta } from "../types";

const CardMetaContext = createContext<Map<number, CardMeta> | null>(null);

export function CardMetaProvider({ children }: { children: ReactNode }) {
  const [cards, setCards] = useState<Map<number, CardMeta> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchCards()
      .then((list) => setCards(new Map(list.map((c) => [c.id, c]))))
      .catch((e) => setError(String(e)));
  }, []);

  if (error) return <div className="error-banner">Failed to load card data: {error}</div>;
  if (!cards) return <div className="loading">Loading card data...</div>;

  return <CardMetaContext.Provider value={cards}>{children}</CardMetaContext.Provider>;
}

export function useCardMeta(): Map<number, CardMeta> {
  const ctx = useContext(CardMetaContext);
  if (!ctx) throw new Error("useCardMeta must be used within a CardMetaProvider");
  return ctx;
}
