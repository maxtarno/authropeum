import { useState } from "react";
import type { RoundResult } from "../lib/types";
import type { Stats } from "../lib/storage";
import { average } from "../lib/storage";
import { haversineKm, yearErrorYears, shareCard } from "../lib/scoring";
import { TIMELINE_START, BLOCK_YEARS } from "../lib/puzzle";

interface Props {
  mode: "daily" | "practice";
  dateStr: string;
  results: RoundResult[];
  stats: Stats;
  onExit: () => void;
}

export default function EndScreen({ mode, dateStr, results, stats, onExit }: Props) {
  const [copied, setCopied] = useState(false);
  const total = results.reduce((sum, r) => sum + r.score.total, 0);

  async function copyScorecard() {
    try {
      await navigator.clipboard.writeText(shareCard(dateStr, results.map((r) => r.score.total)));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // clipboard permission denied — the scorecard is still fully visible on screen
    }
  }

  return (
    <div className="end-screen">
      <h1 className="end-screen-title">{mode === "daily" ? "Daily results" : "Practice results"}</h1>

      <div className="end-tally-row">
        <div className="end-tally">
          <div className="end-stat-label">Final tally</div>
          <div className="end-tally-value">{total.toLocaleString()}</div>
        </div>
        <div className="end-stats">
          <div className="end-stat">
            <div className="end-stat-label">Streak</div>
            <div className="end-stat-value">{stats.streak} days</div>
          </div>
          <div className="end-stat">
            <div className="end-stat-label">Personal best</div>
            <div className="end-stat-value">{stats.best.toLocaleString()}</div>
          </div>
          <div className="end-stat">
            <div className="end-stat-label">Average</div>
            <div className="end-stat-value">{average(stats).toLocaleString()}</div>
          </div>
          <div className="end-stat">
            <div className="end-stat-label">Games played</div>
            <div className="end-stat-value">{stats.gamesPlayed}</div>
          </div>
        </div>
      </div>

      <div className="end-table-wrap">
        <table className="end-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Artifact</th>
              <th>Distance</th>
              <th>Geo</th>
              <th>Year err</th>
              <th>Time</th>
              <th>Total</th>
            </tr>
          </thead>
          <tbody>
            {results.map((r, i) => {
              const distanceKm = Math.round(haversineKm(r.guess.lat, r.guess.lng, r.artifact.lat, r.artifact.lng));
              const yearErr = yearErrorYears(r.guess.block, r.artifact.year_start, r.artifact.year_end, TIMELINE_START, BLOCK_YEARS);
              return (
                <tr key={i}>
                  <td className="end-table-num">{i + 1}</td>
                  <td className="end-table-artifact">
                    <img src={r.artifact.image_url} alt="" className="end-table-thumb" />
                    <span className="end-table-title">{r.artifact.title}</span>
                  </td>
                  <td>{distanceKm.toLocaleString()} km</td>
                  <td>{r.score.geo.toLocaleString()}</td>
                  <td>{yearErr === 0 ? "—" : `${yearErr.toLocaleString()} yrs`}</td>
                  <td>{r.score.time.toLocaleString()}</td>
                  <td className="end-table-total">{r.score.total.toLocaleString()}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="end-actions">
        <button type="button" className="end-action-primary" onClick={onExit}>
          Go to menu
        </button>
        <button type="button" className="end-action-secondary" onClick={copyScorecard}>
          {copied ? "Copied!" : "Share your scorecard"}
        </button>
      </div>
    </div>
  );
}
