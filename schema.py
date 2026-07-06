"""Unified artifact schema.

Every museum adapter must emit Artifact objects in exactly this shape.
This is the ONLY representation the game layer ever sees — the game has
no knowledge of which museum an artifact came from beyond `source`.

Conventions:
  * Years are integers. Negative = BCE (e.g. -1981 = 1981 BCE).
  * geo_confidence ∈ {"site", "region", "country", "culture"} — how precisely
    we know the origin. Used by puzzle selection (prefer precise) and could
    soften scoring later.
  * image_url should be a mid-size web image (~800-1200px), NOT the
    full-resolution original.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional

CURRENT_YEAR = 2026

GEO_CONFIDENCE_LEVELS = ("site", "region", "country", "culture")


@dataclass
class Artifact:
    # Identity
    source: str                      # "met" | "cleveland" | "aic" | ...
    source_id: str                   # museum's own id, as string
    title: str

    # Image
    image_url: str                   # primary web-size image
    image_urls_extra: list[str] = field(default_factory=list)

    # Time (the answer, dimension 1)
    year_start: int = 0
    year_end: int = 0

    # Place (the answer, dimension 2)
    lat: float = 0.0
    lng: float = 0.0
    geo_confidence: str = "country"
    geo_display: str = ""            # human-readable answer, e.g. "Meir, Egypt"
    geo_qualifier: str = ""          # e.g. "probably from", "" if certain

    # Display / reveal
    medium: str = ""                 # shown as a hint during play
    culture_display: str = ""        # e.g. "Middle Kingdom, Dynasty 12"
    artist_display: str = ""
    reveal_text: str = ""            # post-guess story (CMA description etc.)
    reveal_text_license: str = ""    # "CC0" | "CC-BY" (AIC descriptions)
    credit: str = ""                 # museum credit line
    object_url: str = ""             # link back to the museum page

    # Curation signals (not shown to player)
    is_highlight: bool = False
    department: str = ""
    classification: str = ""
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def uid(self) -> str:
        return f"{self.source}:{self.source_id}"


class RejectRecord(Exception):
    """Raised by adapters/validators when a record can't become a playable artifact."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


def validate(a: Artifact, max_range_years: int = 700) -> Artifact:
    """Quality gates. Every artifact must pass before entering the pool.

    max_range_years: reject objects whose creation window is too wide to be
    fair to guess against a 250-year block (default 700 = tunable).
    """
    if not a.title or not a.title.strip():
        raise RejectRecord("missing title")
    if not a.image_url:
        raise RejectRecord("missing image")
    if a.year_start == 0 and a.year_end == 0:
        raise RejectRecord("missing dates")
    if a.year_start > a.year_end:
        raise RejectRecord(f"inverted date range {a.year_start}..{a.year_end}")
    if a.year_end > CURRENT_YEAR:
        raise RejectRecord(f"year_end {a.year_end} in the future")
    if a.year_start < -3200:
        # Timeline starts at 3000 BCE; allow slight spill for edge scoring.
        raise RejectRecord(f"year_start {a.year_start} predates timeline")
    if (a.year_end - a.year_start) > max_range_years:
        raise RejectRecord(
            f"date range too wide ({a.year_end - a.year_start}y) to guess fairly"
        )
    if a.lat == 0.0 and a.lng == 0.0:
        raise RejectRecord("unresolved geography")
    if a.geo_confidence not in GEO_CONFIDENCE_LEVELS:
        raise RejectRecord(f"bad geo_confidence {a.geo_confidence!r}")
    if not a.geo_display:
        raise RejectRecord("missing geo_display answer string")
    return a
