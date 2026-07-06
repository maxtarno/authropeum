"""Consolidation pipeline: raw museum records → one standardized artifact pool.

    python3 pipeline.py --source cleveland --limit 500
    python3 pipeline.py --source met --highlights
    python3 pipeline.py --source aic --limit 500
    python3 pipeline.py --fixtures            # offline test with bundled samples

Each run APPENDS/UPDATES output/artifacts.json (keyed by source:id), so you
can ingest sources incrementally. Rejections and gazetteer misses are written
to output/rejects.log and output/geo_misses.json — feed the misses back into
geo.GAZETTEER to grow coverage.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from schema import Artifact, RejectRecord, validate
from geo import GeoResolver
from adapters import met, cleveland, aic

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
POOL_PATH = os.path.join(OUT_DIR, "artifacts.json")

ADAPTERS = {"met": met, "cleveland": cleveland, "aic": aic}


def load_pool() -> dict[str, dict]:
    if os.path.exists(POOL_PATH):
        with open(POOL_PATH) as f:
            return {a["source"] + ":" + a["source_id"]: a for a in json.load(f)}
    return {}


def save_pool(pool: dict[str, dict]) -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    arts = sorted(pool.values(), key=lambda a: (a["source"], a["source_id"]))
    with open(POOL_PATH, "w") as f:
        json.dump(arts, f, indent=1, ensure_ascii=False)


def run(records, adapter, geo: GeoResolver, pool: dict[str, dict],
        rejects: list[str]) -> tuple[int, int]:
    ok = bad = 0
    for rec in records:
        try:
            art = validate(adapter.normalize(rec, geo))
            pool[art.uid] = art.to_dict()
            ok += 1
        except RejectRecord as e:
            rid = rec.get("objectID") or rec.get("id") or "?"
            rejects.append(f"{adapter.__name__}:{rid}\t{e.reason}")
            bad += 1
        except Exception as e:  # malformed record — never kill the run
            rejects.append(f"{adapter.__name__}:?\tERROR {e}")
            bad += 1
    return ok, bad


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source", choices=ADAPTERS.keys())
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--highlights", action="store_true",
                   help="met/cleveland: only star objects (great starter pool)")
    p.add_argument("--aic-dump", help="path to extracted AIC data dump")
    p.add_argument("--fixtures", action="store_true",
                   help="offline run against bundled sample records")
    args = p.parse_args()

    geo = GeoResolver()
    pool = load_pool()
    rejects: list[str] = []

    if args.fixtures:
        fx_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
        for name, adapter in ADAPTERS.items():
            path = os.path.join(fx_dir, f"{name}.json")
            with open(path) as f:
                ok, bad = run(json.load(f), adapter, geo, pool, rejects)
            print(f"[{name:9}] fixtures: {ok} accepted, {bad} rejected")
    else:
        if not args.source:
            p.error("--source required (or use --fixtures)")
        adapter = ADAPTERS[args.source]
        if args.source == "met":
            records = met.iter_records(highlights_only=args.highlights, limit=args.limit)
        elif args.source == "cleveland":
            records = cleveland.iter_records(highlights_only=args.highlights, limit=args.limit)
        elif args.aic_dump:
            records = aic.iter_dump(args.aic_dump)
        else:
            records = aic.iter_records(limit=args.limit)
        ok, bad = run(records, adapter, geo, pool, rejects)
        print(f"[{args.source:9}] live: {ok} accepted, {bad} rejected")

    save_pool(pool)
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "rejects.log"), "a") as f:
        f.write("\n".join(rejects) + ("\n" if rejects else ""))
    with open(os.path.join(OUT_DIR, "geo_misses.json"), "w") as f:
        json.dump(dict(sorted(geo.misses.items(), key=lambda kv: -kv[1])), f,
                  indent=1, ensure_ascii=False)

    print(f"pool now contains {len(pool)} artifacts → {POOL_PATH}")
    if geo.misses:
        print(f"{len(geo.misses)} unresolved geo strings → output/geo_misses.json "
              f"(add the frequent ones to geo.GAZETTEER)")


if __name__ == "__main__":
    main()
