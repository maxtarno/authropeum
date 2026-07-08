import { describe, expect, it } from "vitest";
import type { Artifact } from "./types";
import {
  blockLabel,
  blockOf,
  buildDailyPuzzle,
  buildPracticePuzzle,
  continentOf,
  ERA_PRESETS,
  formatYear,
  matchesFilter,
  N_BLOCKS,
  selectDaily,
  styleOf,
} from "./puzzle";

describe("blockOf", () => {
  it.each([
    [-3000, 0],
    [-2751, 0],
    [-2750, 1],
    [1999, 19],
    [2000, 19], // clamps at the final block
    [2500, 19], // anything past 2000 CE also clamps
    [-4000, 0], // anything before 3000 BCE clamps to the first block
  ])("blockOf(%i) === %i", (year, expected) => {
    expect(blockOf(year)).toBe(expected);
  });
});

describe("formatYear / blockLabel", () => {
  it("formats BCE and CE", () => {
    expect(formatYear(-500)).toBe("500 BCE");
    expect(formatYear(500)).toBe("500 CE");
    expect(formatYear(0)).toBe("0 CE");
  });

  it("labels the first and last blocks", () => {
    expect(blockLabel(0)).toBe("3000 BCE – 2750 BCE");
    expect(blockLabel(N_BLOCKS - 1)).toBe("1750 CE – 2000 CE");
  });

  it("labels the block crossing the BCE/CE boundary", () => {
    expect(blockLabel(11)).toBe("250 BCE – 0 CE");
  });
});

describe("continentOf", () => {
  it.each([
    [-33.87, 151.21, "oceania"], // Sydney
    [40.71, -74.01, "americas"], // New York
    [30.04, 31.24, "africa"], // Cairo
    [35.68, 139.69, "asia"], // Tokyo
    [24.71, 46.68, "middle_east"], // Riyadh
    [48.86, 2.35, "europe"], // Paris
  ])("(%d, %d) -> %s", (lat, lng, expected) => {
    expect(continentOf(lat, lng)).toBe(expected);
  });
});

function makeArtifact(overrides: Partial<Artifact>): Artifact {
  return {
    source: "met",
    source_id: "1",
    title: "Test",
    image_url: "https://example.com/x.jpg",
    image_urls_extra: [],
    year_start: 1500,
    year_end: 1500,
    lat: 48,
    lng: 2,
    geo_confidence: "country",
    geo_display: "France",
    geo_qualifier: "",
    medium: "",
    culture_display: "",
    artist_display: "",
    reveal_text: "",
    reveal_text_license: "",
    credit: "",
    object_url: "",
    is_highlight: false,
    department: "",
    classification: "",
    tags: [],
    ...overrides,
  };
}

function makePool(n: number): Artifact[] {
  return Array.from({ length: n }, (_, i) => makeArtifact({ source_id: String(i) }));
}

// Spread across continents/sources/eras so diversity caps don't force
// best-effort relaxation — for tests that just want a full n-round pick.
function makeDiversePool(n: number): Artifact[] {
  const spots: [number, number][] = [
    [-33, 151],
    [40, -74],
    [30, 31],
    [35, 139],
    [24, 46],
    [48, 2],
  ];
  return Array.from({ length: n }, (_, i) => {
    const [lat, lng] = spots[i % spots.length];
    return makeArtifact({
      source_id: String(i),
      source: ["met", "cleveland", "aic"][i % 3],
      lat,
      lng,
      year_start: 1000 + (i % 6) * 300,
      year_end: 1000 + (i % 6) * 300,
    });
  });
}

describe("selectDaily", () => {
  it("is deterministic for the same seed", () => {
    const pool = makePool(50);
    const a = selectDaily(pool, "daily-2026-07-07");
    const b = selectDaily(pool, "daily-2026-07-07");
    expect(a.map((x) => x.source_id)).toEqual(b.map((x) => x.source_id));
  });

  it("differs across seeds", () => {
    const pool = makePool(50);
    const a = selectDaily(pool, "daily-2026-07-07");
    const b = selectDaily(pool, "daily-2026-07-08");
    expect(a.map((x) => x.source_id)).not.toEqual(b.map((x) => x.source_id));
  });

  it("respects the per-continent cap with a diverse pool", () => {
    const pool = makeDiversePool(30);
    const picked = selectDaily(pool, "seed", 10, 3, 5, 3);
    expect(picked).toHaveLength(10);

    const byContinent: Record<string, number> = {};
    for (const a of picked) {
      const c = continentOf(a.lat, a.lng);
      byContinent[c] = (byContinent[c] ?? 0) + 1;
    }
    expect(Math.max(...Object.values(byContinent))).toBeLessThanOrEqual(3);
  });

  it("best-effort-returns fewer than n on a too-small pool", () => {
    const pool = makePool(3);
    expect(selectDaily(pool, "seed")).toHaveLength(3);
  });
});

describe("buildDailyPuzzle", () => {
  it("produces 10 rounds tagged with the given date", () => {
    const pool = makeDiversePool(50);
    const puzzle = buildDailyPuzzle(pool, "2026-07-07");
    expect(puzzle.mode).toBe("daily");
    expect(puzzle.date).toBe("2026-07-07");
    expect(puzzle.rounds).toHaveLength(10);
  });
});

describe("styleOf", () => {
  it.each([
    ["Painting", "painting"],
    ["Oil Paintings", "painting"],
    ["Sculpture", "sculpture"],
    ["Drawing and Watercolor", "prints_drawings"],
    ["Ceramic", "ceramics_glass"],
    ["Arms and Armor", "metal_jewelry"],
    ["Textile", "textiles"],
    ["Photograph", "photography"],
    ["Bound Volume", "manuscripts_books"],
    ["Something Unclassifiable", "other"],
  ])("classification %s -> %s", (classification, expected) => {
    expect(styleOf(makeArtifact({ classification }))).toBe(expected);
  });
});

describe("matchesFilter", () => {
  const artifact = makeArtifact({
    source: "aic",
    lat: 35.68,
    lng: 139.69, // Tokyo
    year_start: 1200,
    year_end: 1250,
    classification: "Sculpture",
  });

  it("all always matches", () => {
    expect(matchesFilter(artifact, { type: "all" })).toBe(true);
  });

  it("era matches on range overlap", () => {
    expect(matchesFilter(artifact, { type: "era", loBlock: blockOf(1000), hiBlock: blockOf(1500) })).toBe(true);
    expect(matchesFilter(artifact, { type: "era", loBlock: blockOf(1600), hiBlock: blockOf(1800) })).toBe(false);
  });

  it("style matches the coarse bucket", () => {
    expect(matchesFilter(artifact, { type: "style", style: "sculpture" })).toBe(true);
    expect(matchesFilter(artifact, { type: "style", style: "painting" })).toBe(false);
  });

  it("region matches continentOf", () => {
    expect(matchesFilter(artifact, { type: "region", continent: "asia" })).toBe(true);
    expect(matchesFilter(artifact, { type: "region", continent: "europe" })).toBe(false);
  });

  it("museum matches by source", () => {
    expect(matchesFilter(artifact, { type: "museum", sources: ["aic", "met"] })).toBe(true);
    expect(matchesFilter(artifact, { type: "museum", sources: ["met"] })).toBe(false);
  });
});

describe("buildPracticePuzzle", () => {
  it("applies the filter before selecting rounds", () => {
    const pool = [
      ...makeDiversePool(20),
      ...Array.from({ length: 5 }, (_, i) =>
        makeArtifact({ source_id: `special-${i}`, lat: -33, lng: 151, year_start: 1900, year_end: 1900 })
      ),
    ];
    const puzzle = buildPracticePuzzle(pool, { type: "region", continent: "oceania" });
    expect(puzzle.mode).toBe("practice");
    for (const a of puzzle.rounds) {
      expect(continentOf(a.lat, a.lng)).toBe("oceania");
    }
  });

  it("falls back to the full pool when nothing matches", () => {
    const pool = makeDiversePool(20);
    const puzzle = buildPracticePuzzle(pool, { type: "museum", sources: ["nonexistent-source"] });
    expect(puzzle.rounds.length).toBeGreaterThan(0);
  });
});

describe("ERA_PRESETS", () => {
  it("covers the full timeline with no gaps", () => {
    expect(ERA_PRESETS[0].loBlock).toBe(0);
    expect(ERA_PRESETS[ERA_PRESETS.length - 1].hiBlock).toBe(N_BLOCKS - 1);
    for (let i = 1; i < ERA_PRESETS.length; i++) {
      expect(ERA_PRESETS[i].loBlock).toBe(ERA_PRESETS[i - 1].hiBlock);
    }
  });
});
