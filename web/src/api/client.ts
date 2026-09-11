import type { ActionRequest, CardMeta, GameStateOut } from "../types";

const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${init?.method ?? "GET"} ${path} -> ${res.status}: ${body}`);
  }
  return res.json() as Promise<T>;
}

export function fetchCards(): Promise<CardMeta[]> {
  return request<CardMeta[]>("/cards");
}

export function createSession(humanSeat: number, seed?: number): Promise<GameStateOut> {
  return request<GameStateOut>("/sessions", {
    method: "POST",
    body: JSON.stringify({ human_seat: humanSeat, seed: seed ?? null }),
  });
}

export function getSession(sessionId: string): Promise<GameStateOut> {
  return request<GameStateOut>(`/sessions/${sessionId}`);
}

export function submitAction(sessionId: string, action: ActionRequest): Promise<GameStateOut> {
  return request<GameStateOut>(`/sessions/${sessionId}/actions`, {
    method: "POST",
    body: JSON.stringify(action),
  });
}
