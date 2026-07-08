# Authropeum-Multi — frontend

React + Vite client for the daily/practice artifact-guessing game. Reads the
consolidated pool the pipeline produces (`../output/artifacts.json`) and does
all puzzle generation and scoring client-side — no server, no cron.

## Quick start

```
npm install
npm run sync-data   # splits ../output/artifacts.json into public/artifacts-index.json + public/details/*.json
npm run dev
```

Re-run `npm run sync-data` any time the pool is re-ingested (`pipeline.py`).

## Data loading

At 30k+ artifacts, `output/artifacts.json` is tens of MB — too much to fetch
before the menu can even render. `sync-data.mjs` splits it in two (see
GAME_SPEC.md's Data contract section for the full rationale):

* `public/artifacts-index.json` — lightweight fields for every artifact,
  enough to pick a puzzle's rounds and drive practice filters. Loads on
  page load.
* `public/details/*.json` — full records, hash-sharded by `source:source_id`.
  Only fetched (a handful of shards, not the whole pool) once a puzzle's
  ~10 rounds are actually chosen — see `lib/details.ts`.

## Layout

```
src/lib/
  types.ts     Artifact/ArtifactIndexEntry/Guess/RoundScore types, mirrors schema.py
  puzzle.ts    timeline blocks, continent bucketing, date-seeded selectDaily
               (TS port of puzzle.py — same algorithm, independently seeded
               PRNG, not bit-parity with Python's random.Random), plus
               practice-only PracticeFilter (era/style/region/museum) and
               styleOf's coarse classification bucketing. Operates on
               ArtifactIndexEntry, not the full Artifact.
  scoring.ts   geo/time scoring + share card, direct port of puzzle.py
  storage.ts   localStorage personal best / average / streak (daily mode
               only); alreadyPlayedToday() gates replaying a finished daily
  session.ts   resumable in-progress session (survives a page reload),
               keyed by puzzle identity — daily mode only resumes if the
               session's date still matches today
  details.ts   fetches full Artifact records for a set of uids by hashing
               each into its shard (lib/detailShards.mjs) and requesting
               only those bucket files, with an in-memory per-bucket cache
  detailShards.mjs  hashBucket() — plain JS (not .ts) so the exact same
               file runs unmodified in both this app and scripts/sync-data.mjs
src/components/
  WorldMap.tsx       click-to-pin map (d3-geo + topojson-client, no map tiles
                     or API keys — bundled world-atlas 110m topology); a
                     coordinate-entry fallback in GameScreen covers keyboard use
  TimelineBlocks.tsx era picker (draggable slider over 250-year blocks)
  RoundCard.tsx      image/title/medium during play (museum name withheld)
  RevealPanel.tsx    true pin/era, reveal text (+ CC-BY attribution for AIC),
                     credit line, museum name, object link, score breakdown
  PracticeSetup.tsx  practice-mode filter picker (Everything/Era/Style/
                     Region/Museum) shown before a practice session starts
  GameScreen.tsx     orchestrates one 10-round session; a round only counts
                     as "finished" once the player clicks through the final
                     round's reveal, not the instant it's revealed
  EndScreen.tsx      final tally, personal-best/streak/average, round-by-round
                     table, share-card copy-to-clipboard (emoji grid + score)
  Wordmark.tsx       "Au" in gold, "thropeum" in the surrounding text color
```

## A note on stats integrity

Personal best/streak/average live in `localStorage` — there's no account or
server, so nothing stops a determined user from clearing site data to reset
their own streak, same as any other localStorage-based daily-streak game
(Wordle included). What the app *does* do:

* Block replaying an already-completed daily puzzle (`alreadyPlayedToday` in
  `storage.ts`, checked in `App.tsx`) — no accidental or casual re-rolling
  for a better score.
* Keep `recordDailyResult` idempotent per calendar date, so even a second
  call for a day already recorded (e.g. two tabs) can't double-count games
  played or reset the streak to 1.

True tamper-resistance (can't be undone by clearing your own browser) would
need real accounts and a server-side source of truth — a different, much
bigger project than "no server, no cron."

## Build

```
npm run build   # tsc -b && vite build -> dist/, static, host-agnostic
```

## Tests

```
npm test   # vitest — scoring.ts and puzzle.ts, mirrors the pytest suite in ../tests
```
