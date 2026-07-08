"""Adapter: Minneapolis Institute of Art (Mia) open-access metadata.

Data: https://github.com/artsmia/collection — one static JSON file per
      object at objects/$bucket/$id.json, where bucket = id // 1000. No API,
      no key; we walk sequential ids and fetch each file straight off the
      raw.githubusercontent.com CDN (no GitHub API calls, so no rate limit).

Metadata is CC0 (https://github.com/artsmia/collection/blob/main/readme.md);
*images* are not — they're under Mia's own "limited non-commercial and
educational" policy, with `restricted: 1` marking anything under tighter
per-object copyright. We only accept `image: "valid"` and `restricted: 0`.

`dated` is a free-text field ("c. 1888–89", "19th century", "1750-1780
B.C.") — the only date source Mia gives us, so it needs a small parser
here rather than clean integer fields like Met/Cleveland/AIC provide.
"""

from __future__ import annotations

import json
import re
import time
import urllib.request

from schema import Artifact, RejectRecord
from geo import GeoResolver

RAW_BASE = "https://raw.githubusercontent.com/artsmia/collection/main/objects"
IMAGE_BASE = "https://api.artsmia.org/images/{id}/large.jpg"
OBJECT_URL = "https://collections.artsmia.org/art/{id}"

_BCE_RE = re.compile(r"\bB\.?C\.?E?\.?\b", re.IGNORECASE)
_CENTURY_RE = re.compile(r"(\d{1,2})(?:st|nd|rd|th)\s+century", re.IGNORECASE)
_YEAR_RANGE_RE = re.compile(r"(\d{3,4})\s*[-–—]\s*(\d{1,4})")
_SINGLE_YEAR_RE = re.compile(r"(\d{3,4})")

# `nationality`/`culture` often carry a bare demonym adjective the gazetteer's
# word-boundary match can't see inside (e.g. "Mexican" doesn't contain
# "mexico" as a substring at all — it needs its own mapping, not just fuzzy
# matching).
DEMONYM = {
    "mexican": "mexico", "japanese": "japan", "chinese": "china",
    "korean": "korea", "thai": "thailand", "spanish": "spain",
    "flemish": "flanders", "italian": "italy", "french": "france",
    "dutch": "netherlands", "german": "germany", "english": "england",
    "british": "england", "indian": "india", "persian": "iran",
    "egyptian": "egypt", "greek": "greece", "peruvian": "peru",
    "guatemalan": "guatemala",
}


def _demonym_candidate(*fields: str) -> str:
    hay = " ".join(fields).lower()
    for demonym, place in DEMONYM.items():
        if demonym in hay:
            return place
    return ""


def _parse_dated(s: str) -> tuple[int, int] | tuple[None, None]:
    """Best-effort parse of Mia's free-text `dated` field."""
    if not s:
        return None, None
    is_bce = bool(_BCE_RE.search(s))

    m = _CENTURY_RE.search(s)
    if m:
        century = int(m.group(1))
        y0, y1 = (century - 1) * 100, century * 100
        return (-y1, -y0) if is_bce else (y0, y1)

    m = _YEAR_RANGE_RE.search(s)
    if m:
        y0_str, y1_str = m.group(1), m.group(2)
        y0 = int(y0_str)
        # "1888-89" -> second year borrows the first year's century prefix
        y1 = int(y1_str) if len(y1_str) >= len(y0_str) else int(y0_str[: len(y0_str) - len(y1_str)] + y1_str)
        # BCE ranges are written largest-first ("945-712 B.C." == 945 BCE to
        # 712 BCE), the opposite chronological direction from CE ranges.
        return (-y0, -y1) if is_bce else (y0, y1)

    m = _SINGLE_YEAR_RE.search(s)
    if m:
        y = int(m.group(1))
        y = -y if is_bce else y
        return y, y

    return None, None


def normalize(rec: dict, geo: GeoResolver) -> Artifact:
    if rec.get("image") != "valid":
        raise RejectRecord("no image")
    if rec.get("restricted"):
        raise RejectRecord("image usage restricted")
    if "public domain" not in (rec.get("rights_type") or "").lower():
        raise RejectRecord("not public domain")

    title = rec.get("title") or rec.get("object_name") or ""
    if not title.strip():
        raise RejectRecord("missing title")

    year_start, year_end = _parse_dated(rec.get("dated") or "")
    if year_start is None:
        raise RejectRecord(f"unparseable date: {rec.get('dated')!r}")

    country, culture, nationality = rec.get("country") or "", rec.get("culture") or "", rec.get("nationality") or ""
    candidates = [country, culture, nationality, _demonym_candidate(country, culture, nationality)]
    g = geo.resolve(candidates)
    if g is None:
        raise RejectRecord(f"geo unresolved: {candidates}")

    fetched_id = rec.get("_fetched_id")
    obj_id = fetched_id if fetched_id is not None else rec.get("id")

    return Artifact(
        source="mia",
        source_id=str(obj_id),
        title=title,
        image_url=IMAGE_BASE.format(id=obj_id),
        image_urls_extra=[],
        year_start=year_start,
        year_end=year_end,
        lat=g.lat,
        lng=g.lng,
        geo_confidence=g.confidence,
        geo_display=g.display,
        geo_qualifier=g.qualifier,
        medium=rec.get("medium") or "",
        culture_display=rec.get("culture") or rec.get("life_date") or "",
        artist_display=rec.get("artist") or "",
        reveal_text=rec.get("text") or "",
        reveal_text_license="CC0" if rec.get("text") else "",
        credit=rec.get("creditline") or "",
        object_url=OBJECT_URL.format(id=obj_id),
        is_highlight=False,
        department=rec.get("department") or "",
        classification=rec.get("classification") or "",
        tags=[],
    )


# ---------------- live fetch (run on your machine) ----------------

def iter_records(limit: int | None = None, start_id: int = 0, max_misses: int = 500, sleep: float = 0.02):
    """Walk sequential object ids off the raw CDN. Ids aren't contiguous, so
    this stops after `max_misses` consecutive 404s rather than a fixed count."""
    fetched = misses = 0
    oid = start_id
    while True:
        bucket = oid // 1000
        url = f"{RAW_BASE}/{bucket}/{oid}.json"
        try:
            with urllib.request.urlopen(url, timeout=15) as r:
                rec = json.loads(r.read())
            if not isinstance(rec, dict):
                oid += 1
                continue
            rec["_fetched_id"] = oid
            yield rec
            fetched += 1
            misses = 0
            if limit and fetched >= limit:
                return
        except urllib.error.HTTPError as e:
            if e.code != 404:
                raise
            misses += 1
            if misses >= max_misses:
                return
        except (json.JSONDecodeError, urllib.error.URLError, TimeoutError, ConnectionError):
            # Transient CDN hiccup — skip this id rather than kill the whole
            # run; a single bad fetch shouldn't lose everything gathered so far.
            pass
        oid += 1
        time.sleep(sleep)
