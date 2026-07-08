# Game Spec — functionally modeled on Anthropeum

## The Anthropeum model (what we replicate)

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

1. **Multi-museum pool.** Rounds draw from Met + Cleveland + AIC (extensible).
   The museum name is hidden during play (it's a strong location tell for
   collection-savvy players) and revealed with the credit line after guessing.
2. **Single-player.** No percentile curve; the frontend should show personal
   best, average, and streak from localStorage instead.
3. **Reveal moment.** After each guess: true pin + era, `geo_display` answer
   string (with "probably from" qualifier when the museum itself is unsure),
   `reveal_text` story where available (CMA `did_you_know` is a goldmine),
   credit line, and a link to the object page.
4. **Client-side daily generation.** The puzzle is derived deterministically
   from the date (SHA-256 seed) against the shipped pool — no server, no cron.

## Daily selection constraints (`select_daily`)

* ≤3 artifacts per continent bucket
* ≤3 per era block (prevents the "all Roman stuff" complaint real Anthropeum
  players have)
* ≤5 per source museum
* Caps auto-relax if the pool can't satisfy them.

## Data contract

The game reads exactly one file: `output/artifacts.json`, a list of unified
Artifact objects (see `schema.py`). Required by the game per round:

```
image_url, title, medium                    → shown during play
lat, lng, year_start, year_end              → scoring truth
geo_display, geo_qualifier, culture_display,
artist_display, reveal_text (+license), credit, object_url → reveal screen
```

Curation fields (`is_highlight`, `department`, `classification`, `tags`,
`geo_confidence`) drive selection, never display.
