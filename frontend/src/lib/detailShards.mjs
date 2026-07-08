// Plain JS (not .ts) so this same file can run unmodified in both the Node
// build script (scripts/sync-data.mjs) and the Vite/browser bundle
// (src/lib/puzzle.ts) — one hash, guaranteed to agree on which bucket a
// given artifact landed in, since both are just JS running on a spec that
// nails down `Math.imul`/`charCodeAt`/`|0` bit-for-bit.

export const N_DETAIL_BUCKETS = 128;

export function hashBucket(uid, nBuckets = N_DETAIL_BUCKETS) {
  let h = 0;
  for (let i = 0; i < uid.length; i++) {
    h = (Math.imul(31, h) + uid.charCodeAt(i)) | 0;
  }
  return Math.abs(h) % nBuckets;
}
