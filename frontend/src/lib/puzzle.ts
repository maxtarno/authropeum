import type { Artifact } from "./types";

export const TIMELINE_START = -3000;
export const TIMELINE_END = 2000;
export const BLOCK_YEARS = 250;
export const N_BLOCKS = (TIMELINE_END - TIMELINE_START) / BLOCK_YEARS; // 20

export function blockOf(year: number): number {
  return Math.max(0, Math.min(N_BLOCKS - 1, Math.floor((year - TIMELINE_START) / BLOCK_YEARS)));
}

export function formatYear(y: number): string {
  return y < 0 ? `${-y} BCE` : `${y} CE`;
}

export function blockLabel(i: number): string {
  const a = TIMELINE_START + i * BLOCK_YEARS;
  const b = a + BLOCK_YEARS;
  return `${formatYear(a)} – ${formatYear(b)}`;
}

export const BLOCK_LABELS = Array.from({ length: N_BLOCKS }, (_, i) => blockLabel(i));

// Coarse bucketing for daily-selection diversity caps, mirrors puzzle.py's continent_of.
export function continentOf(lat: number, lng: number): string {
  if (lat < -12 && lng >= 110 && lng <= 180) return "oceania";
  if (lng < -30) return "americas";
  if (lat < 12 && lng >= -20 && lng <= 55) return "africa";
  if (lat < 36 && lng >= -20 && lng <= 35 && lat > 12) return "africa";
  if (lng > 60) return "asia";
  if (lat < 42 && lng > 25) return "middle_east";
  return "europe";
}

// --- deterministic seeding: xmur3 string hash -> mulberry32 PRNG ---
// Only needs to be deterministic per date across all players, not bit-parity
// with puzzle.py's Python `random.Random` seeding.
function xmur3(str: string): () => number {
  let h = 1779033703 ^ str.length;
  for (let i = 0; i < str.length; i++) {
    h = Math.imul(h ^ str.charCodeAt(i), 3432918353);
    h = (h << 13) | (h >>> 19);
  }
  return () => {
    h = Math.imul(h ^ (h >>> 16), 2246822519);
    h = Math.imul(h ^ (h >>> 13), 3266489917);
    h ^= h >>> 16;
    return h >>> 0;
  };
}

function mulberry32(seed: number): () => number {
  let a = seed;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function seededRandom(seed: string): () => number {
  const hash = xmur3(seed);
  return mulberry32(hash());
}

function seededShuffle<T>(arr: T[], rand: () => number): T[] {
  const out = arr.slice();
  for (let i = out.length - 1; i > 0; i--) {
    const j = Math.floor(rand() * (i + 1));
    [out[i], out[j]] = [out[j], out[i]];
  }
  return out;
}

export function selectDaily(
  pool: Artifact[],
  seed: string,
  n = 10,
  maxPerContinent = 3,
  maxPerSource = 5,
  maxPerEra = 3
): Artifact[] {
  const rand = seededRandom(seed);
  const shuffled = seededShuffle(pool, rand);

  let picked: Artifact[] = [];
  for (let relax = 0; relax < 3; relax++) {
    picked = [];
    const byCont: Record<string, number> = {};
    const bySrc: Record<string, number> = {};
    const byEra: Record<number, number> = {};
    const cc = maxPerContinent + relax;
    const cs = maxPerSource + relax * 2;
    const ce = maxPerEra + relax;

    for (const a of shuffled) {
      const cont = continentOf(a.lat, a.lng);
      const era = blockOf(a.year_end);
      if ((byCont[cont] ?? 0) >= cc) continue;
      if ((bySrc[a.source] ?? 0) >= cs) continue;
      if ((byEra[era] ?? 0) >= ce) continue;
      picked.push(a);
      byCont[cont] = (byCont[cont] ?? 0) + 1;
      bySrc[a.source] = (bySrc[a.source] ?? 0) + 1;
      byEra[era] = (byEra[era] ?? 0) + 1;
      if (picked.length === n) return picked;
    }
  }
  return picked; // best effort, same as puzzle.py
}

export interface Puzzle {
  mode: "daily" | "practice";
  date: string | null;
  rounds: Artifact[];
}

export function buildDailyPuzzle(pool: Artifact[], dateStr: string): Puzzle {
  return { mode: "daily", date: dateStr, rounds: selectDaily(pool, `daily-${dateStr}`) };
}

export function buildPracticePuzzle(pool: Artifact[]): Puzzle {
  const seed = `practice-${Math.random()}`;
  return { mode: "practice", date: null, rounds: selectDaily(pool, seed) };
}
