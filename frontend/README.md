# Anthropeum-Multi — frontend

React + Vite client for the daily/practice artifact-guessing game. Reads the
consolidated pool the pipeline produces (`../output/artifacts.json`) and does
all puzzle generation and scoring client-side — no server, no cron.

## Quick start

```
npm install
npm run sync-data   # copies ../output/artifacts.json -> public/artifacts.json
npm run dev
```

Re-run `npm run sync-data` any time the pool is re-ingested (`pipeline.py`).

## Layout

```
src/lib/
  types.ts     Artifact/Guess/RoundScore types, mirrors schema.py
  puzzle.ts    timeline blocks, continent bucketing, date-seeded selectDaily
               (TS port of puzzle.py — same algorithm, independently seeded
               PRNG, not bit-parity with Python's random.Random), plus
               practice-only PracticeFilter (era/style/region/museum) and
               styleOf's coarse classification bucketing
  scoring.ts   geo/time scoring + share card, direct port of puzzle.py
  storage.ts   localStorage personal best / average / streak (daily mode only)
  session.ts   resumable in-progress session (survives a page reload),
               keyed by puzzle identity — daily mode only resumes if the
               session's date still matches today
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
  GameScreen.tsx     orchestrates one 10-round session
  EndScreen.tsx      final tally, personal-best/streak/average, round-by-round
                     table, share-card copy-to-clipboard (emoji grid + score)
```

## Build

```
npm run build   # tsc -b && vite build -> dist/, static, host-agnostic
```

## Tests

```
npm test   # vitest — scoring.ts and puzzle.ts, mirrors the pytest suite in ../tests
```
