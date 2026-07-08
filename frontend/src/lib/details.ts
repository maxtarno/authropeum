import { hashBucket } from "./detailShards.mjs";
import { uidOf, type Artifact } from "./types";

// One in-memory cache per bucket for the life of the tab — resuming a
// session and then starting a fresh puzzle shouldn't re-fetch the same
// shard twice.
const bucketCache = new Map<number, Promise<Artifact[]>>();

function fetchBucket(bucket: number): Promise<Artifact[]> {
  let pending = bucketCache.get(bucket);
  if (!pending) {
    pending = fetch(`${import.meta.env.BASE_URL}details/${bucket}.json`).then((r) => r.json());
    bucketCache.set(bucket, pending);
  }
  return pending;
}

// Resolves full Artifact records for exactly the given uids ("source:id"),
// fetching only the handful of hash-sharded detail files those uids land
// in rather than the whole pool. See scripts/sync-data.mjs for the writer
// side and detailShards.mjs for the shared hash both sides use.
export async function fetchDetails(uids: string[]): Promise<Map<string, Artifact>> {
  const buckets = Array.from(new Set(uids.map((uid) => hashBucket(uid))));
  const bucketResults = await Promise.all(buckets.map(fetchBucket));
  const byUid = new Map<string, Artifact>();
  for (const records of bucketResults) {
    for (const a of records) byUid.set(uidOf(a), a);
  }
  return byUid;
}
