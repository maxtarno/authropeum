import { useMemo, useState } from "react";
import type { ArtifactIndexEntry } from "../lib/types";
import {
  CONTINENTS,
  CONTINENT_LABELS,
  ERA_PRESETS,
  STYLE_LABELS,
  type Continent,
  type PracticeFilter,
  type StyleBucket,
  matchesFilter,
} from "../lib/puzzle";

const SOURCE_NAMES: Record<string, string> = {
  met: "The Metropolitan Museum of Art",
  cleveland: "Cleveland Museum of Art",
  aic: "Art Institute of Chicago",
  mia: "Minneapolis Institute of Art",
  walters: "The Walters Art Museum",
  smk: "SMK — National Gallery of Denmark",
  museums_victoria: "Museums Victoria",
  vam: "Victoria and Albert Museum",
  smithsonian: "Smithsonian Open Access",
  harvard: "Harvard Art Museums",
};

type Category = "all" | "era" | "style" | "region" | "museum";

interface Props {
  pool: ArtifactIndexEntry[];
  onStart: (filter: PracticeFilter) => void;
  onBack: () => void;
}

export default function PracticeSetup({ pool, onStart, onBack }: Props) {
  const [category, setCategory] = useState<Category>("all");
  const [era, setEra] = useState<(typeof ERA_PRESETS)[number]>(ERA_PRESETS[0]);
  const [style, setStyle] = useState<StyleBucket>("painting");
  const [region, setRegion] = useState<Continent>("europe");
  const [sources, setSources] = useState<string[]>([]);

  const sourcesInPool = useMemo(() => Array.from(new Set(pool.map((a) => a.source))).sort(), [pool]);

  const filter: PracticeFilter = useMemo(() => {
    switch (category) {
      case "era":
        return { type: "era", loBlock: era.loBlock, hiBlock: era.hiBlock };
      case "style":
        return { type: "style", style };
      case "region":
        return { type: "region", continent: region };
      case "museum":
        return { type: "museum", sources: sources.length ? sources : sourcesInPool };
      default:
        return { type: "all" };
    }
  }, [category, era, style, region, sources, sourcesInPool]);

  const matchCount = useMemo(
    () => (filter.type === "all" ? pool.length : pool.filter((a) => matchesFilter(a, filter)).length),
    [pool, filter]
  );

  function toggleSource(src: string) {
    setSources((prev) => (prev.includes(src) ? prev.filter((s) => s !== src) : [...prev, src]));
  }

  return (
    <div className="practice-setup">
      <p className="eyebrow">Practice — unrecorded</p>
      <h1>Choose what to practice.</h1>

      <div className="category-chips">
        {(["all", "era", "style", "region", "museum"] as Category[]).map((c) => (
          <button
            key={c}
            type="button"
            className={`category-chip${category === c ? " category-chip-active" : ""}`}
            onClick={() => setCategory(c)}
          >
            {c === "all" ? "Everything" : c[0].toUpperCase() + c.slice(1)}
          </button>
        ))}
      </div>

      {category === "era" && (
        <div className="practice-subpicker">
          {ERA_PRESETS.map((p) => (
            <button
              key={p.label}
              type="button"
              className={`practice-option${era.label === p.label ? " practice-option-active" : ""}`}
              onClick={() => setEra(p)}
            >
              {p.label}
            </button>
          ))}
        </div>
      )}

      {category === "style" && (
        <div className="practice-subpicker">
          {(Object.keys(STYLE_LABELS) as StyleBucket[])
            .filter((s) => s !== "other")
            .map((s) => (
              <button
                key={s}
                type="button"
                className={`practice-option${style === s ? " practice-option-active" : ""}`}
                onClick={() => setStyle(s)}
              >
                {STYLE_LABELS[s]}
              </button>
            ))}
        </div>
      )}

      {category === "region" && (
        <div className="practice-subpicker">
          {CONTINENTS.map((c) => (
            <button
              key={c}
              type="button"
              className={`practice-option${region === c ? " practice-option-active" : ""}`}
              onClick={() => setRegion(c)}
            >
              {CONTINENT_LABELS[c]}
            </button>
          ))}
        </div>
      )}

      {category === "museum" && (
        <div className="practice-subpicker">
          {sourcesInPool.map((src) => (
            <button
              key={src}
              type="button"
              className={`practice-option${sources.includes(src) ? " practice-option-active" : ""}`}
              onClick={() => toggleSource(src)}
            >
              {SOURCE_NAMES[src] ?? src}
            </button>
          ))}
        </div>
      )}

      <p className="practice-match-count">
        {matchCount.toLocaleString()} matching object{matchCount === 1 ? "" : "s"}
      </p>

      <div className="mode-select-actions">
        <button type="button" className="btn-primary" disabled={matchCount === 0} onClick={() => onStart(filter)}>
          Start practice
        </button>
        <button type="button" className="btn-secondary" onClick={onBack}>
          Back
        </button>
      </div>
    </div>
  );
}
