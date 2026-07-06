import { copyFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const src = path.join(here, "..", "..", "output", "artifacts.json");
const dest = path.join(here, "..", "public", "artifacts.json");

copyFileSync(src, dest);
console.log(`synced ${src} -> ${dest}`);
