import { useEffect, useState } from "react";
import type { Artifact } from "./lib/types";
import { buildDailyPuzzle, buildPracticePuzzle, type Puzzle } from "./lib/puzzle";
import GameScreen from "./components/GameScreen";
import "./App.css";

function todayStr(): string {
  return new Date().toISOString().slice(0, 10);
}

function App() {
  const [pool, setPool] = useState<Artifact[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [puzzle, setPuzzle] = useState<Puzzle | null>(null);

  useEffect(() => {
    fetch("/artifacts.json")
      .then((r) => r.json())
      .then(setPool)
      .catch(() => setError("Couldn't load the artifact pool (public/artifacts.json)."));
  }, []);

  if (error) return <div className="app-error">{error}</div>;
  if (!pool) return <div className="app-loading">Loading…</div>;

  if (puzzle) {
    return <GameScreen puzzle={puzzle} onExit={() => setPuzzle(null)} />;
  }

  return (
    <div className="mode-select">
      <h1>Anthropeum-Multi</h1>
      <p>Guess where and when each artifact is from.</p>
      <button type="button" onClick={() => setPuzzle(buildDailyPuzzle(pool, todayStr()))}>
        Play today's puzzle
      </button>
      <button type="button" onClick={() => setPuzzle(buildPracticePuzzle(pool))}>
        Practice (random, unrecorded)
      </button>
    </div>
  );
}

export default App;
