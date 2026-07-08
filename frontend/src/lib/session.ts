import type { Puzzle } from "./puzzle";
import type { Artifact, Guess, RoundResult, RoundScore } from "./types";

const KEY = "anthropeum-multi:session:v1";

interface Pin {
  lat: number;
  lng: number;
}

interface PersistedRoundResult {
  uid: string;
  guess: Guess;
  score: RoundScore;
}

interface PersistedSession {
  mode: "daily" | "practice";
  date: string | null;
  roundUids: string[];
  roundIndex: number;
  pin: Pin | null;
  block: number | null;
  revealed: boolean;
  results: PersistedRoundResult[];
}

export interface ResumedState {
  roundIndex: number;
  pin: Pin | null;
  block: number | null;
  revealed: boolean;
  results: RoundResult[];
}

export function uidOf(a: Artifact): string {
  return `${a.source}:${a.source_id}`;
}

export function saveSession(
  puzzle: Puzzle,
  state: { roundIndex: number; pin: Pin | null; block: number | null; revealed: boolean; results: RoundResult[] }
): void {
  const session: PersistedSession = {
    mode: puzzle.mode,
    date: puzzle.date,
    roundUids: puzzle.rounds.map(uidOf),
    roundIndex: state.roundIndex,
    pin: state.pin,
    block: state.block,
    revealed: state.revealed,
    results: state.results.map((r) => ({ uid: uidOf(r.artifact), guess: r.guess, score: r.score })),
  };
  try {
    localStorage.setItem(KEY, JSON.stringify(session));
  } catch {
    // storage full/unavailable — resuming just won't work, not fatal
  }
}

export function clearSession(): void {
  try {
    localStorage.removeItem(KEY);
  } catch {
    // ignore
  }
}

// Re-hydrates a persisted session against the currently loaded pool. Returns
// null (and lets the caller fall back to the normal menu) for anything that
// can't be safely resumed: a new day started, or the pool no longer contains
// one of the referenced artifacts.
export function resolveSession(pool: Artifact[], todayStr: string): { puzzle: Puzzle; state: ResumedState } | null {
  let session: PersistedSession;
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return null;
    session = JSON.parse(raw) as PersistedSession;
  } catch {
    return null;
  }

  if (session.mode === "daily" && session.date !== todayStr) {
    clearSession();
    return null;
  }

  const byUid = new Map(pool.map((a) => [uidOf(a), a]));

  const rounds: Artifact[] = [];
  for (const uid of session.roundUids) {
    const a = byUid.get(uid);
    if (!a) {
      clearSession();
      return null;
    }
    rounds.push(a);
  }
  if (rounds.length === 0) return null;

  const results: RoundResult[] = [];
  for (const r of session.results) {
    const a = byUid.get(r.uid);
    if (!a) {
      clearSession();
      return null;
    }
    results.push({ artifact: a, guess: r.guess, score: r.score });
  }

  return {
    puzzle: { mode: session.mode, date: session.date, rounds },
    state: {
      roundIndex: session.roundIndex,
      pin: session.pin,
      block: session.block,
      revealed: session.revealed,
      results,
    },
  };
}
