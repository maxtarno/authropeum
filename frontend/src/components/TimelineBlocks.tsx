import { BLOCK_LABELS } from "../lib/puzzle";

interface Props {
  selected: number | null;
  onSelect: (block: number) => void;
}

export default function TimelineBlocks({ selected, onSelect }: Props) {
  return (
    <div className="timeline-blocks" role="radiogroup" aria-label="Era">
      {BLOCK_LABELS.map((label, i) => (
        <button
          key={i}
          type="button"
          role="radio"
          aria-checked={selected === i}
          className={`timeline-block${selected === i ? " selected" : ""}`}
          onClick={() => onSelect(i)}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
