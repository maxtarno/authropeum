"""Adapter: Harvard Art Museums.

*** Needs a free API key — untested against live data. ***
Sign up at https://harvardartmuseums.org/collections/api (instant email),
then either export HARVARD_API_KEY or pass api_key= to iter_records().

API: https://api.harvardartmuseums.org/object — key required as `apikey`.
     Non-commercial use only per their terms; images for many 20th/21st
     century works are excluded for rights reasons (that's fine — they're
     simply absent rather than mislabeled, and normalize() rejects on
     missing image like every other adapter here).

`datebegin`/`dateend` are clean signed integers (BCE negative) — no
free-text date parsing needed. `culture` is a plain string ("Greek",
"Flemish") at the top level; `people[].culture`/`birthplace` are a
fallback when the object-level `culture` is empty.
"""

from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request

from schema import Artifact, RejectRecord
from geo import GeoResolver

BASE = "https://api.harvardartmuseums.org/object"

# The plain paginated list endpoint returns a deliberately small field
# subset (no datebegin/dateend/culture/classification/...) — the `fields`
# param is required to get everything normalize() needs in one request per
# page, rather than a second per-object detail fetch.
FIELDS = ",".join([
    "objectid", "title", "datebegin", "dateend", "culture", "period",
    "classification", "medium", "creditline", "department", "description",
    "commentary", "url", "people", "images", "accesslevel", "imagepermissionlevel",
])


def normalize(rec: dict, geo: GeoResolver) -> Artifact:
    if rec.get("accesslevel") != 1:
        raise RejectRecord("restricted record")
    if rec.get("imagepermissionlevel") not in (0, None):
        raise RejectRecord("image display restricted")

    images = rec.get("images") or []
    image_url = images[0].get("baseimageurl") if images else ""
    if not image_url:
        raise RejectRecord("no image")

    y0, y1 = rec.get("datebegin"), rec.get("dateend")
    if y0 is None or y1 is None:
        raise RejectRecord("missing datebegin/dateend")

    people = rec.get("people") or []
    candidates = [rec.get("culture") or ""]
    for p in people:
        candidates += [p.get("culture") or "", p.get("birthplace") or ""]
    g = geo.resolve(candidates)
    if g is None:
        raise RejectRecord(f"geo unresolved: {candidates}")

    title = rec.get("title") or ""
    if not title.strip():
        raise RejectRecord("missing title")

    artist_display = "; ".join(p.get("displayname", "") for p in people if p.get("displayname"))

    return Artifact(
        source="harvard",
        source_id=str(rec.get("objectid") or rec.get("id")),
        title=title,
        image_url=image_url,
        image_urls_extra=[i.get("baseimageurl", "") for i in images[1:3] if i.get("baseimageurl")],
        year_start=int(y0),
        year_end=int(y1),
        lat=g.lat,
        lng=g.lng,
        geo_confidence=g.confidence,
        geo_display=g.display,
        geo_qualifier=g.qualifier,
        medium=rec.get("medium") or "",
        culture_display=rec.get("culture") or rec.get("period") or "",
        artist_display=artist_display,
        reveal_text=(rec.get("commentary") or rec.get("description") or "").strip(),
        reveal_text_license="",
        credit=rec.get("creditline") or "",
        object_url=rec.get("url") or "",
        is_highlight=False,
        department=rec.get("department") or "",
        classification=rec.get("classification") or "",
        tags=[],
    )


# ---------------- live fetch (needs HARVARD_API_KEY — run on your machine) ----------------

def iter_records(limit: int | None = None, api_key: str | None = None, page_size: int = 100, sleep: float = 0.2):
    key = api_key or os.environ.get("HARVARD_API_KEY")
    if not key:
        raise RuntimeError("Harvard adapter needs an API key: export HARVARD_API_KEY=... "
                            "(sign up at https://harvardartmuseums.org/collections/api)")

    page, fetched = 1, 0
    while True:
        qs = urllib.parse.urlencode({"apikey": key, "size": page_size, "page": page, "hasimage": 1, "fields": FIELDS})
        with urllib.request.urlopen(f"{BASE}?{qs}", timeout=30) as r:
            payload = json.loads(r.read())
        records = payload.get("records") or []
        if not records:
            return
        for rec in records:
            yield rec
            fetched += 1
            if limit and fetched >= limit:
                return
        page += 1
        time.sleep(sleep)
