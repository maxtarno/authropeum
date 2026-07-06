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
