const KEY = "authropeum-multi:stats:v1";

export interface Stats {
  best: number;
  totalScore: number;
  gamesPlayed: number;
  streak: number;
  lastPlayedDate: string | null;
}

function defaultStats(): Stats {
  return { best: 0, totalScore: 0, gamesPlayed: 0, streak: 0, lastPlayedDate: null };
}

function load(): Stats {
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? { ...defaultStats(), ...JSON.parse(raw) } : defaultStats();
  } catch {
    return defaultStats();
  }
}

function save(stats: Stats): void {
  localStorage.setItem(KEY, JSON.stringify(stats));
}

function isConsecutiveDay(prev: string, next: string): boolean {
  const prevDate = new Date(`${prev}T00:00:00Z`);
  const nextDate = new Date(`${next}T00:00:00Z`);
  const diffDays = Math.round((nextDate.getTime() - prevDate.getTime()) / 86_400_000);
  return diffDays === 1;
}

// Only daily-mode results affect streak/personal-best; practice runs are unrecorded per GAME_SPEC.
export function recordDailyResult(dateStr: string, total: number): Stats {
  const stats = load();
  stats.best = Math.max(stats.best, total);
  stats.totalScore += total;
  stats.gamesPlayed += 1;
  stats.streak = stats.lastPlayedDate && isConsecutiveDay(stats.lastPlayedDate, dateStr) ? stats.streak + 1 : 1;
  stats.lastPlayedDate = dateStr;
  save(stats);
  return stats;
}

export function getStats(): Stats {
  return load();
}

export function average(stats: Stats): number {
  return stats.gamesPlayed === 0 ? 0 : Math.round(stats.totalScore / stats.gamesPlayed);
}
