// Mirrors api/schemas.py. Keep these in sync by hand -- the project is small
// enough that a codegen step would be more ceremony than value.

export type Category = "gwang" | "animal" | "ribbon" | "junk";

export interface CardMeta {
  id: number;
  month: number;
  category: Category;
  name: string;
}

export interface PlayerOut {
  seat: number;
  hand: number[] | null; // null (hidden) for any seat other than the viewer
  hand_count: number;
  captured: number[];
  go_count: number;
  score: number;
}

export interface EventOut {
  type: string;
  player: number | null;
  card_ids: number[];
  pi_penalty: number;
  note: string;
}

export interface ResultOut {
  winner: number | null;
  scores: number[];
  nagari: boolean;
}

export type PendingDecision = "PLAY_CARD" | "BOMB_DECISION" | "GO_STOP" | "HAND_OVER";

export interface GameStateOut {
  session_id: string;
  viewer_seat: number;
  turn: number;
  pending_decision: PendingDecision;
  legal_options: (number | string)[];
  players: PlayerOut[];
  field: number[];
  deck_count: number;
  hand_over: boolean;
  result: ResultOut | null;
  recent_events: EventOut[];
}

export type ActionRequest =
  | { type: "play_card"; card_id: number }
  | { type: "declare_bomb"; month: number }
  | { type: "skip_bomb" }
  | { type: "go" }
  | { type: "stop" };
