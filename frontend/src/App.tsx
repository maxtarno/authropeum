import { useEffect, useState } from "react";
import type { ArtifactIndexEntry } from "./lib/types";
import { uidOf } from "./lib/types";
import { buildDailyPuzzle, buildPracticePuzzle, type IndexPuzzle, type PracticeFilter, type Puzzle } from "./lib/puzzle";
import { fetchDetails } from "./lib/details";
import { resolveSession, type ResumedState } from "./lib/session";
import { alreadyPlayedToday, getStats } from "./lib/storage";
import GameScreen from "./components/GameScreen";
import PracticeSetup from "./components/PracticeSetup";
import Wordmark from "./components/Wordmark";
import "./App.css";

function todayStr(): string {
  return new Date().toISOString().slice(0, 10);
}

const HEADLINES = [
  "Random Knowledge, GO!",
  "Gemini can't help you now",
  "Worldliest Citizen",
  "You wouldn't confuse India and Pakistan",
  "Do this instead of studying. Hypothetically for the LSATs",
];

async function hydrate(indexPuzzle: IndexPuzzle): Promise<Puzzle> {
  const byUid = await fetchDetails(indexPuzzle.rounds.map(uidOf));
  return { ...indexPuzzle, rounds: indexPuzzle.rounds.map((a) => byUid.get(uidOf(a))!) };
}

function App() {
  const [pool, setPool] = useState<ArtifactIndexEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [puzzle, setPuzzle] = useState<Puzzle | null>(null);
  const [resumed, setResumed] = useState<ResumedState | null>(null);
  const [showPracticeSetup, setShowPracticeSetup] = useState(false);
  const [preparingPuzzle, setPreparingPuzzle] = useState(false);
  const [headlineIndex, setHeadlineIndex] = useState(0);

  useEffect(() => {
    const id = setInterval(() => {
      setHeadlineIndex((i) => (i + 1) % HEADLINES.length);
    }, 3200);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    fetch(`${import.meta.env.BASE_URL}artifacts-index.json`)
      .then((r) => r.json())
      .then(async (data: ArtifactIndexEntry[]) => {
        setPool(data);
        const resolved = await resolveSession(todayStr());
        if (resolved) {
          setPuzzle(resolved.puzzle);
          setResumed(resolved.state);
        }
      })
      .catch(() => setError("Couldn't load the artifact pool (public/artifacts-index.json)."));
  }, []);

  async function startPuzzle(indexPuzzle: IndexPuzzle) {
    setPreparingPuzzle(true);
    const hydrated = await hydrate(indexPuzzle);
    setPuzzle(hydrated);
    setPreparingPuzzle(false);
  }

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
  if (preparingPuzzle) return <div className="app-status app-status-loading">Preparing puzzle…</div>;

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
          setShowPracticeSetup(false);
          startPuzzle(buildPracticePuzzle(pool, filter));
        }}
      />
    );
  }

  const today = todayStr();
  const playedToday = alreadyPlayedToday(today);
  const stats = getStats();

  return (
    <div className="mode-select">
      <p className="eyebrow">
        <Wordmark /> — daily artifact game
      </p>
      <h1 key={headlineIndex} className="headline-cycle">
        {HEADLINES[headlineIndex]}
      </h1>
      <p className="mode-select-sub">
        Objects from museum open-access collections around the world. Pin the map, place the era, meet the answer.
      </p>
      <div className="mode-select-actions">
        {playedToday ? (
          <p className="mode-select-done">
            Today's puzzle is done — you scored <strong>{stats.lastTotal.toLocaleString()}</strong>. Come back
            tomorrow for a new one, or keep practicing below.
          </p>
        ) : (
          <button type="button" className="btn-primary" onClick={() => startPuzzle(buildDailyPuzzle(pool, today))}>
            Play today's puzzle
          </button>
        )}
        <button type="button" className="btn-secondary" onClick={() => setShowPracticeSetup(true)}>
          Practice (unrecorded)
        </button>
      </div>
    </div>
  );
}

export default App;
