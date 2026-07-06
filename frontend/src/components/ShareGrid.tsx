import { useState } from "react";
import { shareCard } from "../lib/scoring";

interface Props {
  dateStr: string;
  roundTotals: number[];
  best: number;
  average: number;
  streak: number;
}

export default function ShareGrid({ dateStr, roundTotals, best, average, streak }: Props) {
  const [copied, setCopied] = useState(false);
  const card = shareCard(dateStr, roundTotals);

  async function copy() {
    try {
      await navigator.clipboard.writeText(card);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // clipboard permission denied — user can still select/copy the text manually
    }
  }

  return (
    <div className="share-grid">
      <pre className="share-card-text">{card}</pre>
      <button type="button" onClick={copy}>
        {copied ? "Copied!" : "Copy results"}
      </button>
      <dl className="share-stats">
        <dt>Personal best</dt>
        <dd>{best.toLocaleString()}</dd>
        <dt>Average</dt>
        <dd>{average.toLocaleString()}</dd>
        <dt>Streak</dt>
        <dd>{streak}</dd>
      </dl>
    </div>
  );
}
