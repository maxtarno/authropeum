import type { Guess, RoundScore } from "./types";

export const MAX_GEO = 5000;
export const MAX_TIME = 5000;
export const GEO_DECAY_KM = 1800;
export const TIME_DECAY_BLOCKS = 1.4;

export function haversineKm(lat1: number, lng1: number, lat2: number, lng2: number): number {
  const r = 6371;
  const rad = (d: number) => (d * Math.PI) / 180;
  const p1 = rad(lat1);
  const p2 = rad(lat2);
  const dp = rad(lat2 - lat1);
  const dl = rad(lng2 - lng1);
  const a = Math.sin(dp / 2) ** 2 + Math.cos(p1) * Math.cos(p2) * Math.sin(dl / 2) ** 2;
  return 2 * r * Math.asin(Math.sqrt(a));
}

export function geoScore(guessLat: number, guessLng: number, trueLat: number, trueLng: number): number {
  const d = haversineKm(guessLat, guessLng, trueLat, trueLng);
  return Math.round(MAX_GEO * Math.exp(-d / GEO_DECAY_KM));
}

export function timeScore(guessBlock: number, yearStart: number, yearEnd: number, blockOf: (y: number) => number): number {
  const lo = blockOf(yearStart);
  const hi = blockOf(yearEnd);
  if (guessBlock >= lo && guessBlock <= hi) return MAX_TIME;
  const gap = guessBlock < lo ? lo - guessBlock : guessBlock - hi;
  return Math.round(MAX_TIME * Math.exp(-gap / TIME_DECAY_BLOCKS));
}

export function roundScore(
  guess: Guess,
  artifact: { lat: number; lng: number; year_start: number; year_end: number },
  blockOf: (y: number) => number
): RoundScore {
  const geo = geoScore(guess.lat, guess.lng, artifact.lat, artifact.lng);
  const time = timeScore(guess.block, artifact.year_start, artifact.year_end, blockOf);
  return { geo, time, total: geo + time };
}

export function shareEmoji(total: number): string {
  if (total >= 9000) return "🟩";
  if (total >= 7000) return "🟦";
  if (total >= 5000) return "🟨";
  return "🟥";
}

export function shareCard(dateStr: string, roundTotals: number[]): string {
  const grid = roundTotals.map(shareEmoji).join("");
  const sum = roundTotals.reduce((a, b) => a + b, 0);
  return `${dateStr}\n${grid} ${sum.toLocaleString()}`;
}
