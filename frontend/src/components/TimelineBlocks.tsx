import { BLOCK_LABELS, N_BLOCKS } from "../lib/puzzle";

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
      <div className="timeline-ticks" aria-hidden="true">
        {BLOCK_LABELS.map((label, i) => (
          <span key={i} className="timeline-tick" title={label} />
        ))}
      </div>
      <div className="timeline-endpoints" aria-hidden="true">
        <span>{BLOCK_LABELS[0].split("–")[0].trim()}</span>
        <span>{BLOCK_LABELS[N_BLOCKS - 1].split("–")[1].trim()}</span>
      </div>
    </div>
  );
}
