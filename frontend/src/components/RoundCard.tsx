import type { Artifact } from "../lib/types";

interface Props {
  artifact: Artifact;
  roundNumber: number;
  totalRounds: number;
}

// Museum name is deliberately withheld here — it's a strong location tell
// (GAME_SPEC "Our differences" #1) and only revealed on RevealPanel.
export default function RoundCard({ artifact, roundNumber, totalRounds }: Props) {
  return (
    <div className="round-card">
      <div className="round-card-progress">
        Round {roundNumber} / {totalRounds}
      </div>
      <img src={artifact.image_url} alt={artifact.title} className="round-card-image" />
      <h2 className="round-card-title">{artifact.title}</h2>
      {artifact.medium && <p className="round-card-medium">{artifact.medium}</p>}
    </div>
  );
}
