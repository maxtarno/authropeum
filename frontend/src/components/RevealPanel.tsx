import type { Artifact, RoundScore } from "../lib/types";
import { blockLabel, blockOf } from "../lib/puzzle";

const SOURCE_NAMES: Record<string, string> = {
  met: "The Metropolitan Museum of Art",
  cleveland: "Cleveland Museum of Art",
  aic: "Art Institute of Chicago",
};

interface Props {
  artifact: Artifact;
  score: RoundScore;
  guessBlock: number;
  onNext: () => void;
  isLastRound: boolean;
}

export default function RevealPanel({ artifact, score, guessBlock, onNext, isLastRound }: Props) {
  const trueBlockStart = blockLabel(blockOf(artifact.year_start));
  return (
    <div className="reveal-panel">
      <p className="reveal-answer">
        {artifact.geo_qualifier && <em>{artifact.geo_qualifier} </em>}
        <strong>{artifact.geo_display}</strong> · {artifact.year_start}–{artifact.year_end}
      </p>
      <p className="reveal-score">
        📍 {score.geo.toLocaleString()} + 🕓 {score.time.toLocaleString()} ={" "}
        <strong>{score.total.toLocaleString()}</strong> / 10,000
      </p>
      <p className="reveal-your-guess">
        You guessed: {blockLabel(guessBlock)}
        {" · "}true era: {trueBlockStart}
      </p>

      {artifact.reveal_text && (
        <p className="reveal-text">
          {artifact.reveal_text}
          {artifact.reveal_text_license === "CC-BY" && (
            <span className="reveal-attribution"> (text: CC-BY, {SOURCE_NAMES[artifact.source]})</span>
          )}
        </p>
      )}

      <p className="reveal-credit">
        {artifact.credit}
        {artifact.artist_display && ` — ${artifact.artist_display}`}
      </p>
      <p className="reveal-museum">
        {SOURCE_NAMES[artifact.source] ?? artifact.source}
        {artifact.object_url && (
          <>
            {" · "}
            <a href={artifact.object_url} target="_blank" rel="noreferrer">
              View object page
            </a>
          </>
        )}
      </p>

      <button type="button" className="reveal-next" onClick={onNext}>
        {isLastRound ? "See results" : "Next round"}
      </button>
    </div>
  );
}
