import type { Artifact, RoundScore } from "../lib/types";
import { blockLabel, blockOf, BLOCK_YEARS } from "../lib/puzzle";
import { MAX_GEO, MAX_TIME, haversineKm, eraGapBlocks } from "../lib/scoring";
import type { Pin } from "./WorldMap";

const SOURCE_NAMES: Record<string, string> = {
  met: "The Metropolitan Museum of Art",
  cleveland: "Cleveland Museum of Art",
  aic: "Art Institute of Chicago",
};

interface Props {
  artifact: Artifact;
  score: RoundScore;
  guessBlock: number;
  guessPin: Pin;
  onNext: () => void;
  isLastRound: boolean;
}

export default function RevealPanel({ artifact, score, guessBlock, guessPin, onNext, isLastRound }: Props) {
  const trueBlockStart = blockLabel(blockOf(artifact.year_start));
  const distanceKm = Math.round(haversineKm(guessPin.lat, guessPin.lng, artifact.lat, artifact.lng));
  const gap = eraGapBlocks(guessBlock, artifact.year_start, artifact.year_end, blockOf);

  return (
    <div className="reveal-panel">
      <p className="reveal-answer">
        {artifact.geo_qualifier && <em>{artifact.geo_qualifier} </em>}
        <strong>{artifact.geo_display}</strong> · {artifact.year_start}–{artifact.year_end}
      </p>

      <div className="score-breakdown">
        <div className="score-row">
          <div className="score-row-label">
            📍 {distanceKm.toLocaleString()} km from the true spot
          </div>
          <div className="score-bar">
            <div className="score-bar-fill score-bar-geo" style={{ width: `${(score.geo / MAX_GEO) * 100}%` }} />
          </div>
          <div className="score-row-value">
            {score.geo.toLocaleString()} / {MAX_GEO.toLocaleString()}
          </div>
        </div>
        <div className="score-row">
          <div className="score-row-label">
            🕓 {gap === 0 ? "within the correct era" : `${gap} block${gap > 1 ? "s" : ""} off (~${(gap * BLOCK_YEARS).toLocaleString()} yrs)`}
          </div>
          <div className="score-bar">
            <div className="score-bar-fill score-bar-time" style={{ width: `${(score.time / MAX_TIME) * 100}%` }} />
          </div>
          <div className="score-row-value">
            {score.time.toLocaleString()} / {MAX_TIME.toLocaleString()}
          </div>
        </div>
        <p className="score-total">
          Total: <strong>{score.total.toLocaleString()}</strong> / 10,000
        </p>
      </div>

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
