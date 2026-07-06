"""Adapter: The Cleveland Museum of Art Open Access API.

API: https://openaccess-api.clevelandart.org/api/artworks/
     No key required. Supports server-side filters we rely on:
       ?cc0&has_image=1&limit=...&skip=...   (and &highlight for star works)

The cleanest source: pre-parsed integer year ranges, a culture list, a
find_spot for excavated works, three image sizes, and description /
did_you_know fields that become our post-guess reveal text (CC0).
"""

from __future__ import annotations

import json
import time
import urllib.request

from schema import Artifact, RejectRecord
from geo import GeoResolver

BASE = "https://openaccess-api.clevelandart.org/api/artworks/"


def normalize(rec: dict, geo: GeoResolver) -> Artifact:
    if (rec.get("share_license_status") or "").upper() != "CC0":
        raise RejectRecord("not CC0")

    images = rec.get("images") or {}
    web = (images.get("web") or {}).get("url") or ""
    if not web:
        raise RejectRecord("no web image")

    y0 = rec.get("creation_date_earliest")
    y1 = rec.get("creation_date_latest")
    if y0 is None or y1 is None:
        raise RejectRecord("missing creation_date_earliest/latest")

    # --- geography: find_spot (excavated) beats culture strings ---
    cultures = rec.get("culture") or []          # ["China, Jiaxing, 16th century"]
    find_spot = rec.get("find_spot") or ""
    candidates = [find_spot] + list(cultures)
    g = geo.resolve(candidates)
    if g is None:
        raise RejectRecord(f"geo unresolved: {candidates}")

    reveal = rec.get("did_you_know") or rec.get("description") or ""

    return Artifact(
        source="cleveland",
        source_id=str(rec.get("id") or rec.get("accession_number")),
        title=rec.get("title") or "",
        image_url=web,
        image_urls_extra=[],
        year_start=int(y0),
        year_end=int(y1),
        lat=g.lat,
        lng=g.lng,
        geo_confidence=g.confidence,
        geo_display=g.display,
        geo_qualifier=g.qualifier,
        medium=rec.get("technique") or "",
        culture_display="; ".join(cultures),
        artist_display="; ".join(
            (c.get("description") or "") for c in (rec.get("creators") or [])
        ),
        reveal_text=reveal,
        reveal_text_license="CC0",
        credit=(rec.get("tombstone") or "").split(". The Cleveland")[0],
        object_url=rec.get("url") or "",
        is_highlight=bool(rec.get("is_highlight") or rec.get("highlight")),
        department=rec.get("department") or "",
        classification=rec.get("type") or "",
        tags=[],
    )


# ---------------- live fetch (run on your machine) ----------------

def iter_records(limit: int | None = None, highlights_only: bool = False,
                 page_size: int = 100, sleep: float = 0.25):
    """Yield raw CMA records via paginated API with CC0+image filters."""
    skip, fetched = 0, 0
    while True:
        url = f"{BASE}?cc0&has_image=1&limit={page_size}&skip={skip}"
        if highlights_only:
            url += "&highlight"
        with urllib.request.urlopen(url, timeout=30) as r:
            data = json.loads(r.read()).get("data") or []
        if not data:
            return
        for rec in data:
            yield rec
            fetched += 1
            if limit and fetched >= limit:
                return
        skip += page_size
        time.sleep(sleep)
