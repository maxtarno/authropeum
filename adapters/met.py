"""Adapter: The Metropolitan Museum of Art Open Access API.

API: https://collectionapi.metmuseum.org/public/collection/v1
     No key required. Be polite: they suggest staying well under 80 req/s;
     we default to 10/s with retry.

Strategy:
  * /objects?departmentIds=... or /search?hasImages=true&isHighlight=true...
    to enumerate IDs, then /objects/{id} for full records.
  * Filter: isPublicDomain == True and primaryImageSmall present.
  * Dates: objectBeginDate/objectEndDate are already integers (BCE negative).
  * Geography: cascade across ~10 sparse fields, most precise first.
"""

from __future__ import annotations

import json
import time
import urllib.request

from schema import Artifact, RejectRecord
from geo import GeoResolver

BASE = "https://collectionapi.metmuseum.org/public/collection/v1"


def normalize(rec: dict, geo: GeoResolver) -> Artifact:
    """Map one raw Met API object record to the unified schema."""
    if not rec.get("isPublicDomain"):
        raise RejectRecord("not public domain")

    image = rec.get("primaryImageSmall") or rec.get("primaryImage") or ""
    if not image:
        raise RejectRecord("no image")

    # --- geography cascade: most precise first ---
    qualifier = ""
    geo_type = (rec.get("geographyType") or "").strip().rstrip(":").lower()
    if geo_type and geo_type not in ("made in", "from", ""):
        qualifier = geo_type  # "probably from", "possibly made in", ...

    candidates = [
        rec.get("locale") or "",       # "Tomb of Ukhhotep" (rarely resolves alone)
        rec.get("excavation") or "",
        rec.get("subregion") or "",    # "Meir"
        rec.get("city") or "",
        rec.get("region") or "",
        rec.get("state") or "",
        rec.get("country") or "",
        rec.get("culture") or "",      # "Japan", "Byzantine", "China, Ming dynasty"
        rec.get("period") or "",       # "Middle Kingdom", "Edo period"
        rec.get("artistDisplayBio") or "",  # last resort: "Dutch, 1632–1675"
    ]
    g = geo.resolve(candidates, qualifier=qualifier)
    if g is None:
        raise RejectRecord(f"geo unresolved: {candidates}")

    # Build a rich answer string: prefer site match + country context
    geo_display = g.display
    locale = rec.get("locale") or ""
    if locale and locale.lower() not in geo_display.lower():
        geo_display = f"{locale}, {geo_display}"

    y0, y1 = rec.get("objectBeginDate"), rec.get("objectEndDate")
    if y0 is None or y1 is None:
        raise RejectRecord("missing objectBegin/EndDate")

    culture_bits = [b for b in (rec.get("period"), rec.get("dynasty"), rec.get("culture")) if b]

    return Artifact(
        source="met",
        source_id=str(rec["objectID"]),
        title=rec.get("title") or "",
        image_url=image,
        image_urls_extra=(rec.get("additionalImages") or [])[:4],
        year_start=int(y0),
        year_end=int(y1),
        lat=g.lat,
        lng=g.lng,
        geo_confidence=g.confidence,
        geo_display=geo_display,
        geo_qualifier=g.qualifier,
        medium=rec.get("medium") or "",
        culture_display=", ".join(dict.fromkeys(culture_bits)),
        artist_display=rec.get("artistDisplayName") or "",
        reveal_text="",                     # Met API has no description field
        reveal_text_license="",
        credit=rec.get("creditLine") or "",
        object_url=rec.get("objectURL") or "",
        is_highlight=bool(rec.get("isHighlight")),
        department=rec.get("department") or "",
        classification=rec.get("classification") or "",
        tags=[t.get("term", "") for t in (rec.get("tags") or [])],
    )


# ---------------- live fetch (run on your machine) ----------------

def _get(url: str, retries: int = 3) -> dict:
    for i in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return json.loads(r.read())
        except Exception:
            if i == retries - 1:
                raise
            time.sleep(2 ** i)
    return {}


def iter_records(department_ids: list[int] | None = None,
                 highlights_only: bool = False,
                 limit: int | None = None,
                 sleep: float = 0.1):
    """Yield raw Met records. highlights_only uses the search endpoint to
    restrict to isHighlight=true (≈2.5k star objects — a great starter pool)."""
    if highlights_only:
        url = f"{BASE}/search?isHighlight=true&hasImages=true&q=*"
        ids = _get(url).get("objectIDs") or []
    else:
        url = f"{BASE}/objects"
        if department_ids:
            url += "?departmentIds=" + "|".join(map(str, department_ids))
        ids = _get(url).get("objectIDs") or []
    if limit:
        ids = ids[:limit]
    for oid in ids:
        try:
            yield _get(f"{BASE}/objects/{oid}")
        except Exception:
            continue
        time.sleep(sleep)
