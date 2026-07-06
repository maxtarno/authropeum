import { useState } from "react";
import type { Puzzle } from "../lib/puzzle";
import { blockOf } from "../lib/puzzle";
import { roundScore } from "../lib/scoring";
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
    <div className="game-screen">
      <RoundCard artifact={artifact} roundNumber={roundIndex + 1} totalRounds={puzzle.rounds.length} />
      <WorldMap
        guess={pin}
        truth={revealed ? { lat: artifact.lat, lng: artifact.lng } : null}
        onGuess={revealed ? undefined : setPin}
      />
      <TimelineBlocks
        selected={block}
        onSelect={setBlock}
        disabled={revealed}
        trueRange={revealed ? [blockOf(artifact.year_start), blockOf(artifact.year_end)] : null}
      />

      {!revealed && (
        <button type="button" disabled={!pin || block === null} onClick={submitGuess}>
          Submit guess
        </button>
      )}

      {revealed && (
        <RevealPanel
          artifact={artifact}
          score={results[results.length - 1].score}
          guessBlock={block!}
          guessPin={pin!}
          onNext={nextRound}
          isLastRound={isLastRound}
        />
      )}
    </div>
  );
}
