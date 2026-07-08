import { useEffect, useState } from "react";
import type { Artifact } from "./lib/types";
import { buildDailyPuzzle, buildPracticePuzzle, type PracticeFilter, type Puzzle } from "./lib/puzzle";
import { resolveSession, type ResumedState } from "./lib/session";
import GameScreen from "./components/GameScreen";
import PracticeSetup from "./components/PracticeSetup";
import Wordmark from "./components/Wordmark";
import "./App.css";

function todayStr(): string {
  return new Date().toISOString().slice(0, 10);
}

function App() {
  const [pool, setPool] = useState<Artifact[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [puzzle, setPuzzle] = useState<Puzzle | null>(null);
  const [resumed, setResumed] = useState<ResumedState | null>(null);
  const [showPracticeSetup, setShowPracticeSetup] = useState(false);

  useEffect(() => {
    fetch(`${import.meta.env.BASE_URL}artifacts.json`)
      .then((r) => r.json())
      .then((data: Artifact[]) => {
        setPool(data);
        const resolved = resolveSession(data, todayStr());
        if (resolved) {
          setPuzzle(resolved.puzzle);
          setResumed(resolved.state);
        }
      })
      .catch(() => setError("Couldn't load the artifact pool (public/artifacts.json)."));
  }, []);

  if (error) {
    return (
      <div className="app-status">
        <p className="eyebrow">Couldn't load the pool</p>
        <p className="app-status-message">{error}</p>
        <button type="button" className="btn-primary" onClick={() => window.location.reload()}>
          Retry
        </button>
      </div>
    );
  }
  if (!pool) return <div className="app-status app-status-loading">Loading…</div>;

  if (puzzle) {
    return (
      <GameScreen
        puzzle={puzzle}
        initial={resumed ?? undefined}
        onExit={() => {
          setPuzzle(null);
          setResumed(null);
        }}
      />
    );
  }

  if (showPracticeSetup) {
    return (
      <PracticeSetup
        pool={pool}
        onBack={() => setShowPracticeSetup(false)}
        onStart={(filter: PracticeFilter) => {
          setPuzzle(buildPracticePuzzle(pool, filter));
          setShowPracticeSetup(false);
        }}
      />
    );
  }

  return (
    <div className="mode-select">
      <p className="eyebrow">
        <Wordmark /> — daily artifact game
      </p>
      <h1>Guess where and when it was made.</h1>
      <p className="mode-select-sub">
        Objects from museum open-access collections around the world. Pin the map, place the era, meet the answer.
      </p>
      <div className="mode-select-actions">
        <button type="button" className="btn-primary" onClick={() => setPuzzle(buildDailyPuzzle(pool, todayStr()))}>
          Play today's puzzle
        </button>
        <button type="button" className="btn-secondary" onClick={() => setShowPracticeSetup(true)}>
          Practice (unrecorded)
        </button>
      </div>
    </div>
  );
}

export default App;
