"""Adapter: The Art Institute of Chicago public API.

API:  https://api.artic.edu/api/v1/artworks   (paginated, no key)
Dump: https://artic-api-data.s3.amazonaws.com/artic-api-data.tar.bz2
      (~115MB compressed → one {id}.json per artwork; PREFER this for full
      ingest so you never paginate the live API.)

Images: IIIF — https://www.artic.edu/iiif/2/{image_id}/full/843,/0/default.jpg
        (843px is AIC's recommended width.)

Quirks handled here:
  * is_public_domain must be true.
  * date_qualifier_title == "Artist's working dates" means the date range is
    the artist's LIFE, not the object's creation → reject (unfair to guess).
  * description is CC-BY (not CC0) → stored with license flag so the game can
    render attribution alongside it.
  * place_of_origin is a single coarse string ("England"); fall back to
    parsing artist_display ("Dutch, 1632–1675") when it's missing.
"""

from __future__ import annotations

import json
import time
import urllib.request

from schema import Artifact, RejectRecord
from geo import GeoResolver

BASE = "https://api.artic.edu/api/v1/artworks"
IIIF = "https://www.artic.edu/iiif/2/{image_id}/full/843,/0/default.jpg"

FIELDS = ",".join([
    "id", "title", "image_id", "alt_image_ids", "is_public_domain",
    "date_start", "date_end", "date_display", "date_qualifier_title",
    "place_of_origin", "artist_display", "medium_display",
    "credit_line", "description", "short_description", "term_titles",
    "department_title", "artwork_type_title", "is_boosted",
    "latitude", "longitude",
])

DEMONYM = {
    "american": "united states", "french": "france", "dutch": "netherlands",
    "british": "england", "english": "england", "italian": "italy",
    "german": "germany", "spanish": "spain", "japanese": "japan",
    "chinese": "china", "korean": "korea", "indian": "india",
    "flemish": "flanders", "austrian": "austria", "swiss": "switzerland",
    "russian": "russia", "mexican": "mexico", "belgian": "belgium",
}


def normalize(rec: dict, geo: GeoResolver) -> Artifact:
    if not rec.get("is_public_domain"):
        raise RejectRecord("not public domain")
    if not rec.get("image_id"):
        raise RejectRecord("no image")

    dq = (rec.get("date_qualifier_title") or "").lower()
    if "working dates" in dq or "artist's life" in dq:
        raise RejectRecord("date range is artist's life, not object's")

    y0, y1 = rec.get("date_start"), rec.get("date_end")
    if y0 is None or y1 is None:
        raise RejectRecord("missing date_start/date_end")

    # --- geography ---
    candidates = [rec.get("place_of_origin") or ""]
    artist = rec.get("artist_display") or ""
    for demonym, place in DEMONYM.items():
        if demonym in artist.lower():
            candidates.append(place)
            break
    g = geo.resolve(candidates)

    # AIC sometimes ships literal coordinates — trust them over the gazetteer
    if rec.get("latitude") and rec.get("longitude"):
        from geo import GeoResult
        g = GeoResult(
            lat=float(rec["latitude"]), lng=float(rec["longitude"]),
            confidence="site",
            display=(g.display if g else (rec.get("place_of_origin") or "unknown")),
        )
    if g is None:
        raise RejectRecord(f"geo unresolved: {candidates}")

    desc = rec.get("short_description") or rec.get("description") or ""

    return Artifact(
        source="aic",
        source_id=str(rec["id"]),
        title=rec.get("title") or "",
        image_url=IIIF.format(image_id=rec["image_id"]),
        image_urls_extra=[IIIF.format(image_id=i) for i in (rec.get("alt_image_ids") or [])[:3]],
        year_start=int(y0),
        year_end=int(y1),
        lat=g.lat,
        lng=g.lng,
        geo_confidence=g.confidence,
        geo_display=g.display,
        geo_qualifier=g.qualifier if hasattr(g, "qualifier") else "",
        medium=rec.get("medium_display") or "",
        culture_display=rec.get("date_display") or "",
        artist_display=artist,
        reveal_text=desc,
        reveal_text_license="CC-BY" if desc else "",
        credit=rec.get("credit_line") or "",
        object_url=f"https://www.artic.edu/artworks/{rec['id']}",
        is_highlight=bool(rec.get("is_boosted")),
        department=rec.get("department_title") or "",
        classification=rec.get("artwork_type_title") or "",
        tags=rec.get("term_titles") or [],
    )


# ---------------- live fetch (run on your machine) ----------------

def iter_records(limit: int | None = None, page_size: int = 100, sleep: float = 0.5):
    """Paginate the live API. For a FULL ingest, download the data dump
    instead and iterate the json/artworks/*.json files through normalize()."""
    page, fetched = 1, 0
    while True:
        url = f"{BASE}?page={page}&limit={page_size}&fields={FIELDS}"
        with urllib.request.urlopen(url, timeout=30) as r:
            payload = json.loads(r.read())
        data = payload.get("data") or []
        if not data:
            return
        for rec in data:
            yield rec
            fetched += 1
            if limit and fetched >= limit:
                return
        page += 1
        time.sleep(sleep)


def iter_dump(dump_dir: str):
    """Iterate records from the extracted data dump's json/artworks folder."""
    import os
    art_dir = os.path.join(dump_dir, "json", "artworks")
    for fn in os.listdir(art_dir):
        if fn.endswith(".json"):
            with open(os.path.join(art_dir, fn)) as f:
                yield json.load(f)
