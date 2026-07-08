import { useState } from "react";
import type { Puzzle } from "../lib/puzzle";
import { blockOf } from "../lib/puzzle";
import { roundScore, haversineKm } from "../lib/scoring";
import type { RoundResult } from "../lib/types";
import { getStats, recordDailyResult } from "../lib/storage";
import WorldMap, { type Pin } from "./WorldMap";
import TimelineBlocks from "./TimelineBlocks";
import RoundCard from "./RoundCard";
import RevealPanel from "./RevealPanel";
import EndScreen from "./EndScreen";

interface Props {
  puzzle: Puzzle;
  onExit: () => void;
}

function dateLabel(dateStr: string): string {
  return new Date(`${dateStr}T00:00:00Z`).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  });
}

export default function GameScreen({ puzzle, onExit }: Props) {
  const [roundIndex, setRoundIndex] = useState(0);
  const [pin, setPin] = useState<Pin | null>(null);
  const [block, setBlock] = useState<number | null>(null);
  const [revealed, setRevealed] = useState(false);
  const [results, setResults] = useState<RoundResult[]>([]);

  const artifact = puzzle.rounds[roundIndex];
  const isLastRound = roundIndex === puzzle.rounds.length - 1;
  const done = revealed && isLastRound;

  function submitGuess() {
    if (!pin || block === null) return;
    const guess = { ...pin, block };
    const score = roundScore(guess, artifact, blockOf);
    setResults((prev) => [...prev, { artifact, guess, score }]);
    setRevealed(true);
  }

  function nextRound() {
    if (isLastRound) return;
    setRoundIndex((i) => i + 1);
    setPin(null);
    setBlock(null);
    setRevealed(false);
  }

  if (done) {
    const dateStr = puzzle.date ?? new Date().toISOString().slice(0, 10);
    const total = results.reduce((sum, r) => sum + r.score.total, 0);
    const stats = puzzle.mode === "daily" ? recordDailyResult(dateStr, total) : getStats();
    return <EndScreen mode={puzzle.mode} dateStr={dateStr} results={results} stats={stats} onExit={onExit} />;
  }

  return (
    <div className="game-card">
      <header className="game-card-header">
        <div className="game-card-brand">
          <span className="game-card-brand-name">Anthropeum</span>
          <span className="game-card-brand-meta">
            {puzzle.mode === "daily" && puzzle.date ? `Daily · ${dateLabel(puzzle.date)}` : "Practice"}
          </span>
        </div>
        <div className="game-card-progress">
          <span className="eyebrow">
            Round {String(roundIndex + 1).padStart(2, "0")} / {puzzle.rounds.length}
          </span>
          <div className="progress-dots">
            {puzzle.rounds.map((_, i) => (
              <span key={i} className={`progress-dot${i <= roundIndex ? " progress-dot-filled" : ""}`} />
            ))}
          </div>
        </div>
      </header>

      <div className="game-card-body">
        <div className="game-card-col">
          <RoundCard artifact={artifact} />
        </div>
        <div className="game-card-col">
          <section className="game-field">
            <p className="eyebrow">Where was it made?</p>
            <WorldMap
              guess={pin}
              truth={revealed ? { lat: artifact.lat, lng: artifact.lng } : null}
              onGuess={revealed ? undefined : setPin}
            />
            {!revealed && (
              <details className="coord-fallback">
                <summary>Enter coordinates instead</summary>
                <div className="coord-inputs">
                  <label>
                    Lat
                    <input
                      type="number"
                      min={-90}
                      max={90}
                      step="0.1"
                      value={pin?.lat ?? ""}
                      onChange={(e) => setPin({ lat: Number(e.target.value), lng: pin?.lng ?? 0 })}
                    />
                  </label>
                  <label>
                    Lng
                    <input
                      type="number"
                      min={-180}
                      max={180}
                      step="0.1"
                      value={pin?.lng ?? ""}
                      onChange={(e) => setPin({ lat: pin?.lat ?? 0, lng: Number(e.target.value) })}
                    />
                  </label>
                </div>
              </details>
            )}
            {revealed && pin && (
              <div className="map-legend">
                <span className="map-legend-item">
                  <span className="map-legend-swatch map-legend-swatch-guess" /> Your pin
                </span>
                <span className="map-legend-item">
                  <span className="map-legend-swatch map-legend-swatch-truth" /> True origin
                </span>
                <span className="map-legend-distance">
                  ≈ {Math.round(haversineKm(pin.lat, pin.lng, artifact.lat, artifact.lng)).toLocaleString()} km off
                </span>
              </div>
            )}
          </section>
          <section className="game-field">
            <p className="eyebrow">When?</p>
            <TimelineBlocks
              selected={block}
              onSelect={setBlock}
              disabled={revealed}
              trueRange={revealed ? [blockOf(artifact.year_start), blockOf(artifact.year_end)] : null}
            />
          </section>

          {!revealed && (
            <button type="button" className="btn-primary btn-block" disabled={!pin || block === null} onClick={submitGuess}>
              Submit guess
            </button>
          )}
        </div>
      </div>

      {revealed && (
        <RevealPanel
          artifact={artifact}
          score={results[results.length - 1].score}
          guessBlock={block!}
          onNext={nextRound}
          isLastRound={isLastRound}
        />
      )}
    </div>
  );
}
