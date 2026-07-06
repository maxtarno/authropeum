import { BLOCK_LABELS, N_BLOCKS, TIMELINE_START, BLOCK_YEARS, formatYear } from "../lib/puzzle";

interface Props {
  selected: number | null;
  onSelect: (block: number) => void;
  disabled?: boolean;
  // [firstBlock, lastBlock] the artifact's true date range covers — any guess
  // landing in this range scores full time credit. Shown once revealed.
  trueRange?: [number, number] | null;
}

const pctPerBlock = 100 / (N_BLOCKS - 1);
const pctOf = (block: number) => block * pctPerBlock;

const MAJOR_STEP = 4; // label every 4 blocks (1000 years)
const MAJOR_YEARS = Array.from({ length: N_BLOCKS / MAJOR_STEP + 1 }, (_, i) => TIMELINE_START + i * MAJOR_STEP * BLOCK_YEARS);

export default function TimelineBlocks({ selected, onSelect, disabled, trueRange }: Props) {
  const value = selected ?? Math.floor((N_BLOCKS - 1) / 2);
  const [trueLo, trueHi] = trueRange ?? [null, null];

  return (
    <div className="timeline">
      <div className="timeline-label">
        {selected === null ? "Drag to pick an era" : BLOCK_LABELS[selected]}
        {trueRange && (
          <span className="timeline-true-label">
            {" · true era: "}
            {trueLo === trueHi
              ? BLOCK_LABELS[trueLo!]
              : `${BLOCK_LABELS[trueLo!].split("–")[0].trim()} – ${BLOCK_LABELS[trueHi!].split("–")[1].trim()}`}
          </span>
        )}
      </div>
      <div className="timeline-track">
        <div className="timeline-cells" aria-hidden="true">
          {BLOCK_LABELS.map((label, i) => (
            <div key={i} className="timeline-cell" title={label} />
          ))}
        </div>
        {trueRange && (
          <div
            className="timeline-true-range"
            style={{
              left: `${Math.max(0, pctOf(trueLo!) - pctPerBlock / 2)}%`,
              width: `${Math.min(100, pctOf(trueHi!) + pctPerBlock / 2) - Math.max(0, pctOf(trueLo!) - pctPerBlock / 2)}%`,
            }}
          />
        )}
        <input
          type="range"
          min={0}
          max={N_BLOCKS - 1}
          step={1}
          value={value}
          disabled={disabled}
          onChange={(e) => onSelect(Number(e.target.value))}
          className={`timeline-slider${selected === null ? " unset" : ""}`}
          aria-label="Era"
          aria-valuetext={selected === null ? undefined : BLOCK_LABELS[selected]}
        />
      </div>
      <div className="timeline-major-labels" aria-hidden="true">
        {MAJOR_YEARS.map((y, i) => (
          <span key={i}>{formatYear(y)}</span>
        ))}
      </div>
    </div>
  );
}
