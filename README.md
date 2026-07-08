# Anthropeum-Multi — data pipeline & game core

A daily artifact-guessing game modeled functionally on Anthropeum, but drawing
from multiple museums' open access collections, consolidated into one
standardized artifact format.

## Layout

```
schema.py        Unified Artifact schema + quality-gate validation
geo.py           Geography resolver (gazetteer + cascade logic)
adapters/
  met.py                Met Open Access API  → Artifact
  cleveland.py          Cleveland Museum API → Artifact
  aic.py                Art Institute of Chicago API/dump → Artifact
  mia.py                Minneapolis Institute of Art (GitHub JSON dump) → Artifact
  walters.py            Walters Art Museum (CSV dump) → Artifact
  smk.py                Statens Museum for Kunst (Denmark) API → Artifact
  museums_victoria.py   Museums Victoria (Australia) API → Artifact
  vam.py                Victoria and Albert Museum API → Artifact
  smithsonian.py        Smithsonian Open Access bulk JSON (SAAM/NMAfA/CHNDM/...) → Artifact
  harvard.py            Harvard Art Museums API → Artifact (needs HARVARD_API_KEY)
pipeline.py      Orchestrator: ingest → normalize → validate → dedupe → pool
puzzle.py        Game core: timeline, scoring, daily selection, share card
fixtures/        Sample raw records (offline testing)
output/
  artifacts.json     THE consolidated pool — the only file the game reads
  geo_misses.json    Unresolved place strings (feed back into geo.GAZETTEER)
  rejects.log        Every rejected record + reason
```

## Quick start (offline sanity check)

```
python3 pipeline.py --fixtures
python3 puzzle.py --date 2026-07-05
```

## Tests

```
pip install pytest
python3 -m pytest
```

Covers schema validation gates, the scoring/timeline math and daily-selection
diversity caps in `puzzle.py`, and pipeline ingest/dedupe against the bundled
fixtures.

## Real ingest (run on your machine — needs internet)

```
# Starter pool: ~2.5k Met star objects + CMA highlights (an evening)
python3 pipeline.py --source met --highlights
python3 pipeline.py --source cleveland --highlights

# Broader pool
python3 pipeline.py --source cleveland --limit 5000
python3 pipeline.py --source aic --limit 5000

# Full AIC via data dump (recommended over paginating their API):
#   curl -O https://artic-api-data.s3.amazonaws.com/artic-api-data.tar.bz2
#   tar xjf artic-api-data.tar.bz2
python3 pipeline.py --source aic --aic-dump ./artic-api-data

# No-key sources — same incremental pattern
python3 pipeline.py --source mia --limit 6000
python3 pipeline.py --source walters                      # whole CSV, no limit needed
python3 pipeline.py --source smk --limit 5000
python3 pipeline.py --source museums_victoria --limit 3000
python3 pipeline.py --source vam --limit 2500
python3 pipeline.py --source smithsonian --units saam,nmafa,chndm --limit 3000

# Key-gated — sign up for a free key first, then:
export HARVARD_API_KEY=...   # https://harvardartmuseums.org/collections/api
python3 pipeline.py --source harvard --limit 1000
```

Runs are incremental — the pool is keyed by `source:id`, so re-running
updates rather than duplicates.

**Never run two `pipeline.py` invocations concurrently.** Each loads
`output/artifacts.json` once at startup and only writes at the very end, so
an overlapping run will silently clobber whatever the other one saved in the
meantime. Run sources one at a time, sequentially.

## The iteration loop that matters

1. Ingest a batch.
2. Open `output/geo_misses.json` — the most frequent unresolved place strings.
3. Add them to `geo.GAZETTEER` (one line each).
4. Re-run. Coverage compounds fast: ~50 added entries typically unlocks
   thousands of records, because museum place strings are highly repetitive.

## Adding a museum later (Rijksmuseum, Smithsonian, ...)

Write one file in `adapters/` exposing `normalize(rec, geo) -> Artifact` and
an `iter_records()` generator. Raise `RejectRecord` for anything unplayable.
Register it in `pipeline.ADAPTERS`. Nothing else changes — the game layer
only ever sees `output/artifacts.json`.

See [SOURCES.md](SOURCES.md) for a researched list of candidate open-access
APIs/dumps, ranked by integration effort.

## Notes

* AIC reveal text is CC-BY → the game must show attribution when
  `reveal_text_license == "CC-BY"`. Everything else displayed is CC0.
* Fixtures are realistic but hand-assembled from documented API responses —
  treat them as pipeline tests, not authoritative museum data.
* `puzzle.py` constants (GEO_DECAY_KM, TIME_DECAY_BLOCKS, diversity caps) are
  the game-feel tuning knobs.
