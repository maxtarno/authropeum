"""Adapter: Statens Museum for Kunst (SMK), the National Gallery of Denmark.

API: https://api.smk.dk/api/v1/art/search/  — no key, paginated (offset/rows).
     `filters=[has_image:true]` restricts to objects with a reproduction.

SMK gives real ISO dates in `production_date[].start/end` (no free-text
parsing needed), but no explicit place-of-origin field — the closest signal
is `production[].creator_nationality`, a Danish-language adjective ("Italiensk",
"Fransk", "Tysk", ...), so this adapter carries its own small Danish
demonym table rather than reusing geo.py's English one.

`public_domain` is a boolean per object — CC0 when true; we reject
everything else rather than guess at a license.
"""

from __future__ import annotations

import json
import time
import urllib.request
import urllib.parse

from schema import Artifact, RejectRecord
from geo import GeoResolver

BASE = "https://api.smk.dk/api/v1/art/search/"

# Danish nationality adjective -> country (SMK's `creator_nationality` field
# is in Danish, so geo.py's English DEMONYM-style gazetteer keys can't see it).
DANISH_DEMONYM = {
    "italiensk": "italy", "fransk": "france", "tysk": "germany",
    "hollandsk": "netherlands", "nederlandsk": "netherlands",
    "engelsk": "england", "britisk": "england", "spansk": "spain",
    "dansk": "denmark", "svensk": "sweden", "norsk": "norway",
    "russisk": "russia", "østrigsk": "austria", "schweizisk": "switzerland",
    "belgisk": "belgium", "polsk": "poland", "japansk": "japan",
    "kinesisk": "china", "amerikansk": "united states", "finsk": "finland",
    "græsk": "greece", "tyrkisk": "turkey", "portugisisk": "portugal",
    "grønlandsk": "greenland", "islandsk": "iceland",
}


def _danish_nationality_candidate(production: list[dict]) -> str:
    for p in production:
        nat = (p.get("creator_nationality") or "").strip().lower()
        if nat in DANISH_DEMONYM:
            return DANISH_DEMONYM[nat]
    return ""


def normalize(rec: dict, geo: GeoResolver) -> Artifact:
    if not rec.get("public_domain"):
        raise RejectRecord("not public domain")

    image_url = rec.get("image_native") or rec.get("image_thumbnail") or ""
    if not image_url:
        raise RejectRecord("no image")

    dates = rec.get("production_date") or []
    if not dates:
        raise RejectRecord("missing production_date")
    start = dates[0].get("start")
    end = dates[0].get("end")
    if not start or not end:
        raise RejectRecord("missing production_date start/end")
    year_start, year_end = int(start[:4]), int(end[:4])

    production = rec.get("production") or []
    nationality_place = _danish_nationality_candidate(production)
    g = geo.resolve([nationality_place])
    if g is None:
        raise RejectRecord(f"geo unresolved: nationality={[p.get('creator_nationality') for p in production]}")

    titles = rec.get("titles") or []
    title = titles[0].get("title") if titles else ""
    if not title:
        raise RejectRecord("missing title")

    object_names = rec.get("object_names") or []
    classification = object_names[0].get("name") if object_names else ""

    creators = "; ".join(p.get("creator") or "" for p in production if p.get("creator"))

    return Artifact(
        source="smk",
        source_id=str(rec["id"]),
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
        medium="; ".join(t.get("term", "") for t in (rec.get("techniques") or []) if isinstance(t, dict)) or "",
        culture_display=dates[0].get("period") or "",
        artist_display=creators,
        reveal_text="",
        reveal_text_license="",
        credit=rec.get("responsible_department") or "",
        object_url=rec.get("object_url") or rec.get("frontend_url") or "",
        is_highlight=False,
        department=rec.get("responsible_department") or "",
        classification=classification or "",
        tags=[],
    )


# ---------------- live fetch (run on your machine) ----------------

def iter_records(limit: int | None = None, rows: int = 100, sleep: float = 0.2):
    """Paginate the SMK search API, restricted to objects with an image."""
    offset, fetched = 0, 0
    while True:
        qs = urllib.parse.urlencode({
            "keys": "*",
            "filters": "[has_image:true],[public_domain:true]",
            "offset": offset,
            "rows": rows,
        }, safe="[]:,*")
        for attempt in range(3):
            try:
                with urllib.request.urlopen(f"{BASE}?{qs}", timeout=30) as r:
                    payload = json.loads(r.read())
                break
            except Exception:
                if attempt == 2:
                    return
                time.sleep(2 ** attempt)
        items = payload.get("items") or []
        if not items:
            return
        for rec in items:
            yield rec
            fetched += 1
            if limit and fetched >= limit:
                return
        offset += rows
        time.sleep(sleep)
