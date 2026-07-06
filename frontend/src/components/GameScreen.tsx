import { useState } from "react";
import type { Puzzle } from "../lib/puzzle";
import { blockOf } from "../lib/puzzle";
import { roundScore } from "../lib/scoring";
import type { RoundScore } from "../lib/types";
import { average, getStats, recordDailyResult } from "../lib/storage";
import WorldMap, { type Pin } from "./WorldMap";
import TimelineBlocks from "./TimelineBlocks";
import RoundCard from "./RoundCard";
import RevealPanel from "./RevealPanel";
import ShareGrid from "./ShareGrid";

interface Props {
  puzzle: Puzzle;
  onExit: () => void;
}

export default function GameScreen({ puzzle, onExit }: Props) {
  const [roundIndex, setRoundIndex] = useState(0);
  const [pin, setPin] = useState<Pin | null>(null);
  const [block, setBlock] = useState<number | null>(null);
  const [revealed, setRevealed] = useState(false);
  const [scores, setScores] = useState<RoundScore[]>([]);

  const artifact = puzzle.rounds[roundIndex];
  const isLastRound = roundIndex === puzzle.rounds.length - 1;
  const done = revealed && isLastRound;

  function submitGuess() {
    if (!pin || block === null) return;
    const score = roundScore({ ...pin, block }, artifact, blockOf);
    setScores((prev) => [...prev, score]);
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
    const totals = scores.map((s) => s.total);
    const dateStr = puzzle.date ?? new Date().toISOString().slice(0, 10);
    const stats = puzzle.mode === "daily" ? recordDailyResult(dateStr, totals.reduce((a, b) => a + b, 0)) : getStats();
    return (
      <div className="game-done">
        <h2>{puzzle.mode === "daily" ? "Daily results" : "Practice results"}</h2>
        <ShareGrid dateStr={dateStr} roundTotals={totals} best={stats.best} average={average(stats)} streak={stats.streak} />
        <button type="button" onClick={onExit}>
          Back to menu
        </button>
      </div>
    );
  }

  return (
    <div className="game-screen">
      <RoundCard artifact={artifact} roundNumber={roundIndex + 1} totalRounds={puzzle.rounds.length} />
      <WorldMap
        guess={pin}
        truth={revealed ? { lat: artifact.lat, lng: artifact.lng } : null}
        onGuess={revealed ? undefined : setPin}
      />
      <TimelineBlocks selected={block} onSelect={revealed ? () => {} : setBlock} />

      {!revealed && (
        <button type="button" disabled={!pin || block === null} onClick={submitGuess}>
          Submit guess
        </button>
      )}

      {revealed && (
        <RevealPanel
          artifact={artifact}
          score={scores[scores.length - 1]}
          guessBlock={block!}
          onNext={nextRound}
          isLastRound={isLastRound}
        />
      )}
    </div>
  );
}
