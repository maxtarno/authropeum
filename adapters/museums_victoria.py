"""Adapter: Museums Victoria (Australia) — Melbourne Museum, Scienceworks,
Immigration Museum, Royal Exhibition Building.

API: https://collections.museumsvictoria.com.au/api/search — no key, just a
     `User-Agent` header. The catalogue mixes humanities/history items with
     natural-science specimens; we restrict to `recordtype=item` (excludes
     zoology/botany/mineralogy specimen records) which still lets through a
     `discipline` of History or Technology, both fine for the game.

Date and place both live in `associations[]`, a list of loosely-typed
"who/what/when/where" entries (Date Made, Date Published, Person Named,
...) — often split across separate entries (one with a date, another with
a place), so we scan the whole list for the best date and best place
independently rather than requiring one entry to carry both.
Licensing is CC BY 4.0 for data; images are marked per-record too.
"""

from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request

from schema import Artifact, RejectRecord
from geo import GeoResolver

BASE = "https://collections.museumsvictoria.com.au/api/search"
USER_AGENT = "Mozilla/5.0 (compatible; authropeum-multi-pipeline/1.0)"

# Trailing "s" allowed so decade notation ("1870s") still matches — a plain
# \b after the digits fails there since "0" and "s" are both word chars.
_YEAR_RE = re.compile(r"\b(1[5-9]\d\d|20\d\d)s?\b")


def _parse_years(s: str) -> tuple[int, int] | tuple[None, None]:
    years = [int(y) for y in _YEAR_RE.findall(s or "")]
    if not years:
        return None, None
    return min(years), max(years)


def _best_date(associations: list[dict]) -> tuple[int, int] | tuple[None, None]:
    for a in associations or []:
        year_start, year_end = _parse_years(a.get("date") or "")
        if year_start is not None:
            return year_start, year_end
    return None, None


def _best_place(associations: list[dict]) -> list[str]:
    for a in associations or []:
        candidates = [a.get("locality") or "", a.get("region") or "", a.get("state") or "", a.get("country") or ""]
        if any(candidates):
            return candidates
    return ["", "", "", ""]


def normalize(rec: dict, geo: GeoResolver) -> Artifact:
    if rec.get("recordType") != "item":
        raise RejectRecord("not a humanities item (likely a specimen)")

    if not (rec.get("licence") or {}).get("shortName"):
        raise RejectRecord("no licence marked")

    media = rec.get("media") or []
    image_url = ""
    for m in media:
        if m.get("type") == "image" and m.get("large", {}).get("uri"):
            image_url = m["large"]["uri"]
            break
    if not image_url:
        raise RejectRecord("no image")

    associations = rec.get("associations") or []

    year_start, year_end = _best_date(associations)
    if year_start is None:
        raise RejectRecord("no association with a parseable date")

    candidates = _best_place(associations)
    g = geo.resolve(candidates)
    if g is None:
        raise RejectRecord(f"geo unresolved: {candidates}")

    maker = next((a.get("name") for a in associations if a.get("type") in ("Made By", "Person Named") and a.get("name")), "")

    title = rec.get("displayTitle") or rec.get("objectName") or ""
    if not title.strip():
        raise RejectRecord("missing title")

    return Artifact(
        source="museums_victoria",
        source_id=str(rec.get("id") or "").split("/")[-1],
        title=title,
        image_url=image_url,
        image_urls_extra=[],
        year_start=year_start,
        year_end=year_end,
        lat=g.lat,
        lng=g.lng,
        geo_confidence=g.confidence,
        geo_display=g.display,
        geo_qualifier=g.qualifier,
        medium=rec.get("physicalDescription") or "",
        culture_display=rec.get("category") or "",
        artist_display=maker,
        reveal_text=(rec.get("objectSummary") or "").strip(),
        reveal_text_license="CC-BY" if rec.get("objectSummary") else "",
        credit=", ".join(rec.get("collectionNames") or []),
        object_url=f"https://collections.museumsvictoria.com.au/{rec.get('id')}" if rec.get("id") else "",
        is_highlight=False,
        department=rec.get("discipline") or "",
        classification=(rec.get("classifications") or [""])[0],
        tags=rec.get("keywords") or [],
    )


# ---------------- live fetch (run on your machine) ----------------

def iter_records(limit: int | None = None, page_size: int = 100, sleep: float = 0.2):
    """Paginate the humanities side of the collection (history/technology/art)."""
    page, fetched = 1, 0
    while True:
        qs = urllib.parse.urlencode({
            "recordtype": "item",
            "hasimages": "yes",
            "page": page,
            "perpage": page_size,
        })
        req = urllib.request.Request(f"{BASE}?{qs}", headers={"User-Agent": USER_AGENT})
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    data = json.loads(r.read())
                break
            except Exception:
                if attempt == 2:
                    return
                time.sleep(2 ** attempt)
        if not data:
            return
        for rec in data:
            yield rec
            fetched += 1
            if limit and fetched >= limit:
                return
        page += 1
        time.sleep(sleep)
