export interface Artifact {
  source: string;
  source_id: string;
  title: string;

  image_url: string;
  image_urls_extra: string[];

  year_start: number;
  year_end: number;

  lat: number;
  lng: number;
  geo_confidence: "site" | "region" | "country" | "culture";
  geo_display: string;
  geo_qualifier: string;

  medium: string;
  culture_display: string;
  artist_display: string;
  reveal_text: string;
  reveal_text_license: "" | "CC0" | "CC-BY";
  credit: string;
  object_url: string;

  is_highlight: boolean;
  department: string;
  classification: string;
  tags: string[];
}

// Fields needed to pick a puzzle's rounds (selectDaily) and support
// practice-mode filters (matchesFilter/styleOf) — everything else about an
// artifact (image, title, reveal text, ...) only ever matters for the ~10
// artifacts a puzzle ends up using, so those are fetched separately as
// "details" once the rounds are chosen. See lib/details.ts.
export type ArtifactIndexEntry = Pick<
  Artifact,
  "source" | "source_id" | "lat" | "lng" | "year_start" | "year_end" | "classification" | "tags"
>;

export function uidOf(a: Pick<Artifact, "source" | "source_id">): string {
  return `${a.source}:${a.source_id}`;
}

export interface Guess {
  lat: number;
  lng: number;
  block: number;
}

export interface RoundScore {
  geo: number;
  time: number;
  total: number;
}

export interface RoundResult {
  artifact: Artifact;
  guess: Guess;
  score: RoundScore;
}
