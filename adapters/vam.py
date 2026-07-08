"""Adapter: Victoria and Albert Museum (V&A), London.

API: https://api.vam.ac.uk/v2 — no key for read access. `/objects/search`
     paginates system numbers; `/museumobject/{systemNumber}` returns the
     full record.

`productionDates[].date.earliest/latest` gives real ISO dates (no free-text
parsing). `placesOfOrigin[].place.text` gives a place name directly.
Images are served through the V&A's IIIF endpoint (framemark.vam.ac.uk) by
image id, one or more of which live in the `images` list.

Rights: V&A publishes collections data under its own terms rather than a
blanket CC0/CC-BY, so `reveal_text` here is left blank rather than
asserting a license we haven't confirmed per-object.
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request

from schema import Artifact, RejectRecord
from geo import GeoResolver

SEARCH_URL = "https://api.vam.ac.uk/v2/objects/search"
OBJECT_URL = "https://api.vam.ac.uk/v2/museumobject/{system_number}"
IMAGE_URL = "https://framemark.vam.ac.uk/collections/{image_id}/full/!843,843/0/default.jpg"


def normalize(rec: dict, geo: GeoResolver) -> Artifact:
    images = rec.get("images") or []
    if not images:
        raise RejectRecord("no image")

    dates = rec.get("productionDates") or []
    earliest = latest = None
    for d in dates:
        date = d.get("date") or {}
        if date.get("earliest") and date.get("latest"):
            earliest, latest = date["earliest"], date["latest"]
            break
    if earliest is None:
        raise RejectRecord("missing productionDates earliest/latest")
    year_start, year_end = int(earliest[:4]), int(latest[:4])

    places = rec.get("placesOfOrigin") or []
    candidates = [(p.get("place") or {}).get("text") or "" for p in places]
    g = geo.resolve(candidates)
    if g is None:
        raise RejectRecord(f"geo unresolved: {candidates}")

    titles = rec.get("titles") or []
    title = (titles[0].get("title") if titles else "") or rec.get("objectType") or ""
    if not title.strip():
        raise RejectRecord("missing title")

    makers = rec.get("artistMakerPeople") or rec.get("artistMakerOrganisations") or []
    artist_display = "; ".join(m.get("name", {}).get("text", "") for m in makers if isinstance(m, dict)) if makers else ""

    return Artifact(
        source="vam",
        source_id=str(rec.get("systemNumber") or rec.get("accessionNumber") or ""),
        title=title,
        image_url=IMAGE_URL.format(image_id=images[0]),
        image_urls_extra=[IMAGE_URL.format(image_id=i) for i in images[1:3]],
        year_start=year_start,
        year_end=year_end,
        lat=g.lat,
        lng=g.lng,
        geo_confidence=g.confidence,
        geo_display=g.display,
        geo_qualifier=g.qualifier,
        medium=rec.get("materialsAndTechniques") or rec.get("materials") or "",
        culture_display=rec.get("briefDescription") or "",
        artist_display=artist_display,
        reveal_text="",
        reveal_text_license="",
        credit=rec.get("creditLine") or "",
        object_url=f"https://collections.vam.ac.uk/item/{rec.get('systemNumber')}" if rec.get("systemNumber") else "",
        is_highlight=False,
        department=rec.get("collectionCode") or "",
        classification=rec.get("objectType") or "",
        tags=list((rec.get("categories") or [])),
    )


# ---------------- live fetch (run on your machine) ----------------

def iter_records(limit: int | None = None, page_size: int = 50, sleep: float = 0.2):
    """Paginates the search endpoint for system numbers, then resolves each
    to a full record. Two requests per object — there's no bulk/dump path."""
    page, fetched = 1, 0
    while True:
        qs = urllib.parse.urlencode({"page": page, "page_size": page_size, "images_exist": "true"})
        for attempt in range(3):
            try:
                with urllib.request.urlopen(f"{SEARCH_URL}?{qs}", timeout=30) as r:
                    payload = json.loads(r.read())
                break
            except Exception:
                if attempt == 2:
                    return
                time.sleep(2 ** attempt)
        records = payload.get("records") or []
        if not records:
            return
        for summary in records:
            system_number = summary.get("systemNumber")
            if not system_number:
                continue
            try:
                with urllib.request.urlopen(OBJECT_URL.format(system_number=system_number), timeout=30) as r:
                    full = json.loads(r.read())
            except Exception:
                continue
            yield full.get("record") or full
            fetched += 1
            time.sleep(sleep)
            if limit and fetched >= limit:
                return
        page += 1
