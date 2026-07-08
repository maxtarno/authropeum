# Game Spec — functionally modeled on Authropeum

## The Authropeum model (what we replicate)

| Mechanic | Rule |
|---|---|
| Daily set | 10 artifacts, one set per calendar day |
| Round input | Map pin (where made) + one era block (when made) |
| Timeline | 3000 BCE → 2000 CE in 250-year blocks (20 blocks) |
| Location score | 0–5,000 pts, distance decay from true origin |
| Time score | 0–5,000 pts; full credit if chosen block overlaps the object's creation range, decaying partial credit for nearby blocks |
| Round max | 10,000 pts; daily max 100,000 |
| Share grid | One emoji per round: 🟩 ≥9,000 · 🟦 ≥7,000 · 🟨 ≥5,000 · 🟥 below; plus total |
| Practice mode | Unlimited random sets, not recorded |
| Round display | Image(s), title, material/medium hint |

Implemented in `puzzle.py`: `block_of`, `geo_score` (exponential decay,
`GEO_DECAY_KM=3000`), `time_score` (overlap → 5,000; else exp decay per block,
`TIME_DECAY_BLOCKS=3.0`), `share_card`.

## Our differences

1. **Multi-museum pool.** Rounds draw from a growing set of open-access
   museums (see `SOURCES.md` for what's built). The museum name is hidden
   during play (it's a strong location tell for collection-savvy players)
   and revealed with the credit line after guessing.
2. **Single-player.** No percentile curve; the frontend should show personal
   best, average, and streak from localStorage instead.
3. **Reveal moment.** After each guess: true pin + era, `geo_display` answer
   string (with "probably from" qualifier when the museum itself is unsure),
   `reveal_text` story where available (CMA `did_you_know` is a goldmine),
   credit line, and a link to the object page.
4. **Client-side daily generation.** The puzzle is derived deterministically
   from the date (SHA-256 seed) against the shipped pool — no server, no cron.
5. **Filtered practice modes.** Daily stays the single unfiltered
   "everything" challenge every player gets, so personal-best/streak stay
   meaningful. Practice can additionally be scoped to an era preset
   (Ancient/Classical/Medieval/Early Modern/Modern), a coarse style bucket
   (painting, sculpture, prints & drawings, ...), a continent, or one or
   more specific museums — see `frontend/src/lib/puzzle.ts`'s
   `PracticeFilter` and `frontend/src/components/PracticeSetup.tsx`.

## Daily selection constraints (`select_daily`)

* ≤3 artifacts per continent bucket
* ≤3 per era block (prevents the "all Roman stuff" complaint real Authropeum
  players have)
* ≤5 per source museum
* Caps auto-relax if the pool can't satisfy them.

## Data contract

The pipeline's source of truth is still one file, `output/artifacts.json` —
a list of unified Artifact objects (see `schema.py`). Required by the game
per round:

```
image_url, title, medium                    → shown during play
lat, lng, year_start, year_end              → scoring truth
geo_display, geo_qualifier, culture_display,
artist_display, reveal_text (+license), credit, object_url → reveal screen
```

Curation fields (`is_highlight`, `department`, `classification`, `tags`,
`geo_confidence`) drive selection, never display.

**The frontend, however, doesn't fetch that file directly** — at 30k+
artifacts it's tens of MB, most of which (image/text/credit fields) is
irrelevant until a specific artifact is actually chosen for a round.
`scripts/sync-data.mjs` splits it into:

* `public/artifacts-index.json` — every artifact, but only the fields
  `selectDaily`/`matchesFilter`/`styleOf` need (source, source_id, lat, lng,
  year_start, year_end, classification, tags). This is what loads on page
  load, before the player has picked a mode.
* `public/details/{0..127}.json` — the full records, hash-sharded by
  `source:source_id` (`lib/detailShards.mjs`, shared between the build
  script and the browser so both agree on which bucket an artifact is in).
  Once a puzzle's ~10 rounds are chosen, only their few shards get fetched
  (`lib/details.ts`) — never the whole pool.
