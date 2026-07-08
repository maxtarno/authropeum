import { describe, expect, it } from "vitest";
import { blockOf } from "./puzzle";
import {
  eraGapBlocks,
  GEO_DECAY_KM,
  geoScore,
  MAX_GEO,
  MAX_TIME,
  roundScore,
  shareCard,
  shareEmoji,
  TIME_DECAY_BLOCKS,
  timeScore,
  yearErrorYears,
} from "./scoring";

describe("geoScore", () => {
  it("is max at zero distance", () => {
    expect(geoScore(30, 40, 30, 40)).toBe(MAX_GEO);
  });

  it("decays monotonically with distance", () => {
    const near = geoScore(0, 0, 0, 1);
    const far = geoScore(0, 0, 0, 90);
    expect(near).toBeGreaterThan(far);
    expect(far).toBeGreaterThan(0);
  });

  it("lands at 1/e of max exactly GEO_DECAY_KM away along the equator", () => {
    // Along the equator, great-circle distance is exactly R * delta-longitude
    // (in radians), so this constructs a point at precisely GEO_DECAY_KM.
    const r = 6371;
    const lng2 = (GEO_DECAY_KM / r) * (180 / Math.PI);
    expect(geoScore(0, 0, 0, lng2)).toBe(Math.round(MAX_GEO * Math.exp(-1)));
  });
});

describe("timeScore", () => {
  it("gives full credit when the guess overlaps the true range", () => {
    const lo = blockOf(-2060);
    expect(timeScore(lo, -2060, -2040, blockOf)).toBe(MAX_TIME);
  });

  it("decays symmetrically on either side of the range", () => {
    const lo = blockOf(-2060);
    const before = timeScore(lo - 2, -2060, -2040, blockOf);
    const after = timeScore(lo + 2, -2060, -2040, blockOf);
    expect(before).toBe(after);
  });

  it("matches the known one-block-off value", () => {
    const lo = blockOf(-2060);
    const score = timeScore(lo - 1, -2060, -2040, blockOf);
    expect(score).toBe(Math.round(MAX_TIME * Math.exp(-1 / TIME_DECAY_BLOCKS)));
  });
});

describe("eraGapBlocks / yearErrorYears", () => {
  it("is zero when the guess overlaps", () => {
    const lo = blockOf(-2060);
    expect(eraGapBlocks(lo, -2060, -2040, blockOf)).toBe(0);
    expect(yearErrorYears(lo, -2060, -2040, -3000, 250)).toBe(0);
  });

  it("counts blocks/years off for a miss", () => {
    const lo = blockOf(-2060);
    expect(eraGapBlocks(lo - 1, -2060, -2040, blockOf)).toBe(1);
    expect(yearErrorYears(lo - 1, -2060, -2040, -3000, 250)).toBeGreaterThan(0);
  });
});

describe("roundScore", () => {
  it("sums geo and time for an exact guess", () => {
    const guess = { lat: 30.96, lng: 46.1, block: blockOf(-2060) };
    const artifact = { lat: 30.96, lng: 46.1, year_start: -2060, year_end: -2040 };
    const result = roundScore(guess, artifact, blockOf);
    expect(result).toEqual({ geo: MAX_GEO, time: MAX_TIME, total: MAX_GEO + MAX_TIME });
  });
});

describe("shareEmoji / shareCard", () => {
  it.each([
    [10000, "🟩"],
    [9000, "🟩"],
    [8999, "🟦"],
    [7000, "🟦"],
    [6999, "🟨"],
    [5000, "🟨"],
    [4999, "🟥"],
    [0, "🟥"],
  ])("shareEmoji(%i) === %s", (total, expected) => {
    expect(shareEmoji(total)).toBe(expected);
  });

  it("formats a share card", () => {
    expect(shareCard("2026-07-07", [9500, 6000, 100])).toBe("2026-07-07\n🟩🟨🟥 15,600");
  });
});
