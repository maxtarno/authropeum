import type { Artifact, RoundScore } from "../lib/types";
import { blockLabel, blockOf } from "../lib/puzzle";
import { MAX_GEO, MAX_TIME, eraGapBlocks } from "../lib/scoring";

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
  const gap = eraGapBlocks(guessBlock, artifact.year_start, artifact.year_end, blockOf);

  return (
    <div className="reveal-panel">
      <div className="reveal-col">
        {artifact.culture_display && <p className="reveal-culture">{artifact.culture_display}</p>}
        {artifact.reveal_text && (
          <div className="reveal-note">
            <p className="eyebrow">Did you know</p>
            <p className="reveal-text">
              {artifact.reveal_text}
              {artifact.reveal_text_license === "CC-BY" && (
                <span className="reveal-attribution"> (text: CC-BY, {SOURCE_NAMES[artifact.source]})</span>
              )}
            </p>
          </div>
        )}
        <div className="reveal-credit-block">
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
                  View object page →
                </a>
              </>
            )}
          </p>
        </div>
      </div>

      <div className="reveal-col">
        <div>
          <p className="reveal-place">
            {artifact.geo_qualifier && <em>{artifact.geo_qualifier} </em>}
            {artifact.geo_display}
          </p>
          <p className="reveal-era-sub">
            {artifact.year_start}–{artifact.year_end} · you guessed {blockLabel(guessBlock)}
            {gap > 0 && ` (${gap} block${gap > 1 ? "s" : ""} off true era: ${trueBlockStart})`}
          </p>
        </div>

        <div className="score-breakdown">
          <div className="score-row">
            <span className="score-row-label">Location</span>
            <div className="score-bar">
              <div className="score-bar-fill score-bar-geo" style={{ width: `${(score.geo / MAX_GEO) * 100}%` }} />
            </div>
            <span className="score-row-value">{score.geo.toLocaleString()}</span>
          </div>
          <div className="score-row">
            <span className="score-row-label">Era</span>
            <div className="score-bar">
              <div className="score-bar-fill score-bar-time" style={{ width: `${(score.time / MAX_TIME) * 100}%` }} />
            </div>
            <span className="score-row-value">{score.time.toLocaleString()}</span>
          </div>
          <div className="score-total-row">
            <span className="eyebrow">Round total</span>
            <span className="score-total">
              {score.total.toLocaleString()} <span className="score-total-max">/ 10,000</span>
            </span>
          </div>
        </div>

        <button type="button" className="btn-outline btn-block" onClick={onNext}>
          {isLastRound ? "See results" : "Next round →"}
        </button>
      </div>
    </div>
  );
}
