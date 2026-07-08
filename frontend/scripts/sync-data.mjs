import { existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { N_DETAIL_BUCKETS, hashBucket } from "../src/lib/detailShards.mjs";

const here = path.dirname(fileURLToPath(import.meta.url));
const src = path.join(here, "..", "..", "output", "artifacts.json");
const publicDir = path.join(here, "..", "public");
const detailsDir = path.join(publicDir, "details");

const pool = JSON.parse(readFileSync(src, "utf8"));

// Index: just enough fields to pick a puzzle's 10 rounds (selectDaily) and
// to support practice-mode filters (matchesFilter/styleOf) — everything
// except title/image/reveal text/credit/etc, which only ever matter for
// the handful of artifacts an actual puzzle ends up using. This is what
// loads up front, before the player has even chosen a mode.
const INDEX_FIELDS = ["source", "source_id", "lat", "lng", "year_start", "year_end", "classification", "tags"];
const index = pool.map((a) => Object.fromEntries(INDEX_FIELDS.map((k) => [k, a[k]])));

// Details: the full record, sharded by a hash of "source:source_id" so a
// puzzle's ~10 artifacts only ever cost a handful of small bucket fetches
// instead of downloading the entire pool. See detailShards.mjs — the same
// hash runs in the browser to know which bucket to ask for.
const buckets = Array.from({ length: N_DETAIL_BUCKETS }, () => []);
for (const a of pool) {
  buckets[hashBucket(`${a.source}:${a.source_id}`)].push(a);
}

rmSync(detailsDir, { recursive: true, force: true });
mkdirSync(detailsDir, { recursive: true });
buckets.forEach((records, i) => {
  writeFileSync(path.join(detailsDir, `${i}.json`), JSON.stringify(records));
});

writeFileSync(path.join(publicDir, "artifacts-index.json"), JSON.stringify(index));

const oldFullPool = path.join(publicDir, "artifacts.json");
if (existsSync(oldFullPool)) rmSync(oldFullPool);

console.log(`synced ${pool.length} artifacts -> ${path.relative(here, publicDir)}/artifacts-index.json`);
console.log(`  + ${N_DETAIL_BUCKETS} detail shards in ${path.relative(here, detailsDir)}/`);
