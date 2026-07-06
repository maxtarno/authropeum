import { BLOCK_LABELS, N_BLOCKS } from "../lib/puzzle";

interface Props {
  selected: number | null;
  onSelect: (block: number) => void;
  disabled?: boolean;
}

export default function TimelineBlocks({ selected, onSelect, disabled }: Props) {
  const value = selected ?? Math.floor((N_BLOCKS - 1) / 2);

  return (
    <div className="timeline">
      <div className="timeline-label">{selected === null ? "Drag to pick an era" : BLOCK_LABELS[selected]}</div>
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
