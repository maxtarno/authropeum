import { useEffect, useState } from "react";
import type { Artifact } from "../lib/types";

interface Props {
  artifact: Artifact;
}

// Museum name is deliberately withheld here — it's a strong location tell
// (GAME_SPEC "Our differences" #1) and only revealed on RevealPanel.
export default function RoundCard({ artifact }: Props) {
  const [failCount, setFailCount] = useState(0);

  // AIC's IIIF server also occasionally times out (separately from the
  // referrer issue below) — one retry recovers most of those.
  useEffect(() => setFailCount(0), [artifact.source_id]);

  function handleError() {
    setTimeout(() => setFailCount((n) => n + 1), 1200);
  }

  const gaveUp = failCount > 1;

  return (
    <div className="round-card">
      <p className="eyebrow">The object</p>
      <div className="round-card-frame">
        {gaveUp ? (
          <div className="round-card-placeholder">Image unavailable</div>
        ) : (
          <img
            key={failCount}
            src={artifact.image_url}
            alt={artifact.title}
            className="round-card-image"
            referrerPolicy="no-referrer"
            onError={handleError}
          />
        )}
      </div>
      <h2 className="round-card-title">{artifact.title}</h2>
      {artifact.medium && (
        <div className="round-card-spec">
          <span className="round-card-spec-label">Material</span>
          <span className="round-card-spec-value">{artifact.medium}</span>
        </div>
      )}
      <p className="round-card-note">Museum, culture, and date are withheld until you guess.</p>
    </div>
  );
}
