import type { Artifact, ArtifactIndexEntry } from "./types";

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

export function selectDaily<A extends ArtifactIndexEntry>(
  pool: A[],
  seed: string,
  n = 10,
  maxPerContinent = 3,
  maxPerSource = 5,
  maxPerEra = 3
): A[] {
  const rand = seededRandom(seed);
  const shuffled = seededShuffle(pool, rand);

  let picked: A[] = [];
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

export interface PuzzleOf<A> {
  mode: "daily" | "practice";
  date: string | null;
  rounds: A[];
}

// What selection produces: just index fields, cheap to compute over the
// whole pool. Turned into a real Puzzle (full Artifact rounds) by fetching
// each round's details once — see lib/details.ts and App.tsx.
export type IndexPuzzle = PuzzleOf<ArtifactIndexEntry>;
export type Puzzle = PuzzleOf<Artifact>;

export function buildDailyPuzzle(pool: ArtifactIndexEntry[], dateStr: string): IndexPuzzle {
  return { mode: "daily", date: dateStr, rounds: selectDaily(pool, `daily-${dateStr}`) };
}

// --- practice-mode filters ---
// Daily stays the single unfiltered "everything" challenge everyone gets
// (see GAME_SPEC) — these only ever apply to buildPracticePuzzle.

export const CONTINENTS = ["africa", "americas", "asia", "europe", "middle_east", "oceania"] as const;
export type Continent = (typeof CONTINENTS)[number];

export const CONTINENT_LABELS: Record<Continent, string> = {
  africa: "Africa",
  americas: "Americas",
  asia: "Asia",
  europe: "Europe",
  middle_east: "Middle East",
  oceania: "Oceania",
};

export type StyleBucket =
  | "painting" | "sculpture" | "prints_drawings" | "ceramics_glass"
  | "metal_jewelry" | "textiles" | "photography" | "manuscripts_books" | "other";

export const STYLE_LABELS: Record<StyleBucket, string> = {
  painting: "Painting",
  sculpture: "Sculpture",
  prints_drawings: "Prints & Drawings",
  ceramics_glass: "Ceramics & Glass",
  metal_jewelry: "Metalwork & Jewelry",
  textiles: "Textiles",
  photography: "Photography",
  manuscripts_books: "Manuscripts & Books",
  other: "Other",
};

// Coarse keyword bucketing over the messy raw classification vocab various
// museums use (singular/plural, different taxonomies) — same spirit as
// continentOf's coarse geography buckets.
const STYLE_KEYWORDS: [StyleBucket, string[]][] = [
  ["photography", ["photograph"]],
  ["prints_drawings", ["print", "drawing", "watercolor"]],
  ["manuscripts_books", ["manuscript", "bound volume", "book"]],
  ["textiles", ["textile", "costume", "lace", "embroidery"]],
  ["metal_jewelry", ["metal", "silver", "gold", "bronze", "jewelry", "arms and armor", "coin"]],
  ["ceramics_glass", ["ceramic", "glass", "porcelain", "pottery"]],
  ["sculpture", ["sculpture", "statue", "relief", "vessel"]],
  ["painting", ["paint"]],
];

export function styleOf(a: Pick<Artifact, "classification" | "tags">): StyleBucket {
  const hay = `${a.classification} ${a.tags.join(" ")}`.toLowerCase();
  for (const [bucket, keywords] of STYLE_KEYWORDS) {
    if (keywords.some((k) => hay.includes(k))) return bucket;
  }
  return "other";
}

export const ERA_PRESETS = [
  { label: "Ancient", loBlock: 0, hiBlock: blockOf(-500) },
  { label: "Classical & Late Antiquity", loBlock: blockOf(-500), hiBlock: blockOf(500) },
  { label: "Medieval", loBlock: blockOf(500), hiBlock: blockOf(1500) },
  { label: "Early Modern", loBlock: blockOf(1500), hiBlock: blockOf(1800) },
  { label: "Modern", loBlock: blockOf(1800), hiBlock: N_BLOCKS - 1 },
] as const;

export type PracticeFilter =
  | { type: "all" }
  | { type: "era"; loBlock: number; hiBlock: number }
  | { type: "style"; style: StyleBucket }
  | { type: "region"; continent: Continent }
  | { type: "museum"; sources: string[] };

export function matchesFilter(a: ArtifactIndexEntry, filter: PracticeFilter): boolean {
  switch (filter.type) {
    case "all":
      return true;
    case "era": {
      const lo = blockOf(a.year_start);
      const hi = blockOf(a.year_end);
      return hi >= filter.loBlock && lo <= filter.hiBlock;
    }
    case "style":
      return styleOf(a) === filter.style;
    case "region":
      return continentOf(a.lat, a.lng) === filter.continent;
    case "museum":
      return filter.sources.includes(a.source);
  }
}

export function buildPracticePuzzle(pool: ArtifactIndexEntry[], filter: PracticeFilter = { type: "all" }): IndexPuzzle {
  const filtered = filter.type === "all" ? pool : pool.filter((a) => matchesFilter(a, filter));
  const seed = `practice-${Math.random()}`;
  return { mode: "practice", date: null, rounds: selectDaily(filtered.length ? filtered : pool, seed) };
}
