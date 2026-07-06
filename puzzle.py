"""Game core, modeled functionally on Anthropeum.

Faithful mechanics:
  * 10 artifacts per daily puzzle.
  * Guess = map pin (lat/lng) + one 250-year era block.
  * Timeline: 3000 BCE → 2000 CE in 250-year blocks (20 blocks); the final
    block absorbs anything after 2000.
  * Per artifact: 0–5,000 location pts + 0–5,000 time pts = 10,000 max;
    100,000 max per day.
  * Time score: full credit if your block overlaps the artifact's creation
    range; decaying partial credit for nearby blocks.
  * Share grid: one emoji per round — 🟩 ≥9000, 🟦 ≥7000, 🟨 ≥5000, 🟥 below.
  * Practice mode = same generator with a random (non-date) seed.

Single-player adaptations (things Anthropeum ties to its player base):
  * No percentile/distribution — the frontend shows personal best / streak.

Usage:
    python3 puzzle.py --date 2026-07-05          # generate today's puzzle
    python3 puzzle.py --practice                 # random practice set
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
POOL_PATH = os.path.join(OUT_DIR, "artifacts.json")

# ---------------- timeline ----------------

TIMELINE_START, TIMELINE_END, BLOCK_YEARS = -3000, 2000, 250
N_BLOCKS = (TIMELINE_END - TIMELINE_START) // BLOCK_YEARS  # 20


def block_of(year: int) -> int:
    """Map a year to its era-block index (0..19). Years past 2000 clamp to 19."""
    return max(0, min(N_BLOCKS - 1, (year - TIMELINE_START) // BLOCK_YEARS))


def block_label(i: int) -> str:
    a = TIMELINE_START + i * BLOCK_YEARS
    b = a + BLOCK_YEARS
    fmt = lambda y: f"{-y} BCE" if y < 0 else f"{y} CE"
    return f"{fmt(a)} – {fmt(b)}"


# ---------------- scoring ----------------

MAX_GEO, MAX_TIME = 5000, 5000
GEO_DECAY_KM = 1800        # e^-1 of geo points gone per 1800 km — tune to taste
TIME_DECAY_BLOCKS = 1.4    # partial credit falloff for near-miss blocks


def haversine_km(lat1, lng1, lat2, lng2) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def geo_score(guess_lat, guess_lng, true_lat, true_lng) -> int:
    d = haversine_km(guess_lat, guess_lng, true_lat, true_lng)
    return round(MAX_GEO * math.exp(-d / GEO_DECAY_KM))


def time_score(guess_block: int, year_start: int, year_end: int) -> int:
    """Full credit if the chosen 250-yr block overlaps [year_start, year_end];
    otherwise decay with distance (in blocks) from the nearest correct block."""
    lo, hi = block_of(year_start), block_of(year_end)
    if lo <= guess_block <= hi:
        return MAX_TIME
    gap = (lo - guess_block) if guess_block < lo else (guess_block - hi)
    return round(MAX_TIME * math.exp(-gap / TIME_DECAY_BLOCKS))


def round_score(guess: dict, artifact: dict) -> dict:
    g = geo_score(guess["lat"], guess["lng"], artifact["lat"], artifact["lng"])
    t = time_score(guess["block"], artifact["year_start"], artifact["year_end"])
    return {"geo": g, "time": t, "total": g + t}


def share_emoji(total: int) -> str:
    if total >= 9000: return "🟩"
    if total >= 7000: return "🟦"
    if total >= 5000: return "🟨"
    return "🟥"


def share_card(date_str: str, round_totals: list[int]) -> str:
    grid = "".join(share_emoji(t) for t in round_totals)
    return f"{date_str}\n{grid} {sum(round_totals):,}"


# ---------------- daily selection ----------------

def continent_of(lat: float, lng: float) -> str:
    """Coarse bucketing for diversity constraints — not geography homework."""
    if lat < -12 and 110 <= lng <= 180: return "oceania"
    if lng < -30:  return "americas"
    if lat < 12 and -20 <= lng <= 55: return "africa"
    if lat < 36 and -20 <= lng <= 35 and lat > 12: return "africa"
    if lng > 60:   return "asia"
    if lat < 42 and lng > 25: return "middle_east"
    return "europe"


def select_daily(pool: list[dict], seed: str, n: int = 10,
                 max_per_continent: int = 3, max_per_source: int = 5,
                 max_per_era: int = 3) -> list[dict]:
    """Deterministic, seed-driven pick with diversity caps.

    Caps: ≤3 per continent bucket, ≤3 per era block, ≤5 per source museum.
    Relaxes caps automatically if the pool is too small to satisfy them.
    """
    rng = random.Random(int(hashlib.sha256(seed.encode()).hexdigest(), 16))
    shuffled = pool[:]
    rng.shuffle(shuffled)

    for relax in range(3):  # progressively loosen caps if needed
        picked, by_cont, by_src, by_era = [], {}, {}, {}
        cc = max_per_continent + relax
        cs = max_per_source + relax * 2
        ce = max_per_era + relax
        for a in shuffled:
            cont = continent_of(a["lat"], a["lng"])
            era = block_of(a["year_end"])
            if by_cont.get(cont, 0) >= cc: continue
            if by_src.get(a["source"], 0) >= cs: continue
            if by_era.get(era, 0) >= ce: continue
            picked.append(a)
            by_cont[cont] = by_cont.get(cont, 0) + 1
            by_src[a["source"]] = by_src.get(a["source"], 0) + 1
            by_era[era] = by_era.get(era, 0) + 1
            if len(picked) == n:
                return picked
    return picked  # best effort


def build_puzzle(date_str: str | None, practice: bool = False) -> dict:
    with open(POOL_PATH) as f:
        pool = json.load(f)
    seed = f"practice-{random.random()}" if practice else f"daily-{date_str}"
    arts = select_daily(pool, seed)
    return {
        "mode": "practice" if practice else "daily",
        "date": date_str,
        "timeline": {"start": TIMELINE_START, "end": TIMELINE_END,
                     "block_years": BLOCK_YEARS,
                     "blocks": [block_label(i) for i in range(N_BLOCKS)]},
        "rounds": arts,
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--date", help="YYYY-MM-DD (daily mode)")
    p.add_argument("--practice", action="store_true")
    args = p.parse_args()
    pz = build_puzzle(args.date, practice=args.practice)
    out = os.path.join(OUT_DIR, f"puzzle-{pz['date'] or 'practice'}.json")
    with open(out, "w") as f:
        json.dump(pz, f, indent=1, ensure_ascii=False)
    print(f"{len(pz['rounds'])} rounds → {out}")
    for a in pz["rounds"]:
        print(f"  [{a['source']:9}] {a['title'][:48]:50} "
              f"{a['year_start']}–{a['year_end']}  {a['geo_display']}")
