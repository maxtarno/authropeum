"""Adapter: The Walters Art Museum open-access collection.

Data: https://github.com/WaltersArtMuseum/api-thewalters-org — static CSVs
      (their live API v1 closed in 2023; v2 isn't out yet). `art.csv` has
      one row per object, `media.csv` has one row per image (join on
      ObjectID, prefer IsPrimary). Both data and images are CC0.

Unlike Mia, `DateBeginYear`/`DateEndYear` are already clean signed integers
(BCE negative) — no free-text date parsing needed here. `Description` is
HTML, same as AIC, so it gets the same tag-stripping treatment.
"""

from __future__ import annotations

import csv
import html
import io
import re
import urllib.request

from schema import Artifact, RejectRecord
from geo import GeoResolver

ART_CSV_URL = "https://raw.githubusercontent.com/WaltersArtMuseum/api-thewalters-org/main/art.csv"
MEDIA_CSV_URL = "https://raw.githubusercontent.com/WaltersArtMuseum/api-thewalters-org/main/media.csv"

_TAG_RE = re.compile(r"<[^>]+>")


def _clean_html(text: str) -> str:
    text = re.sub(r"</?(p|br|div|li)\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = _TAG_RE.sub("", text)
    text = html.unescape(text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


# Culture/Style often carry a bare demonym adjective ("Japanese", "Thai")
# rather than a place name the gazetteer's word-boundary match can see
# inside it — same gap AIC's adapter fills for artist_display.
DEMONYM = {
    "japanese": "japan", "chinese": "china", "thai": "thailand",
    "korean": "korea", "spanish": "spain", "flemish": "flanders",
    "italian": "italy", "french": "france", "dutch": "netherlands",
    "german": "germany", "english": "england", "british": "england",
    "austrian": "austria", "swiss": "switzerland", "russian": "russia",
    "mexican": "mexico", "belgian": "belgium", "indian": "india",
    "persian": "iran", "egyptian": "egypt", "greek": "greece",
    "ethiopian": "ethiopia", "turkish": "turkey", "syrian": "syria",
}


def _demonym_candidate(*fields: str) -> str:
    hay = " ".join(fields).lower()
    for demonym, place in DEMONYM.items():
        if demonym in hay:
            return place
    return ""


def normalize(rec: dict, geo: GeoResolver) -> Artifact:
    title = rec.get("Title") or rec.get("ObjectName") or ""
    if not title.strip():
        raise RejectRecord("missing title")

    image_url = rec.get("_image_url") or ""
    if not image_url:
        raise RejectRecord("no image")

    y0, y1 = rec.get("DateBeginYear"), rec.get("DateEndYear")
    if not y0 or not y1:
        raise RejectRecord("missing DateBeginYear/DateEndYear")

    culture, style, period = rec.get("Culture") or "", rec.get("Style") or "", rec.get("Period") or ""
    candidates = [culture, style, period, _demonym_candidate(culture, style, period)]
    g = geo.resolve(candidates)
    if g is None:
        raise RejectRecord(f"geo unresolved: {candidates}")

    desc = _clean_html(rec.get("Description") or "")

    return Artifact(
        source="walters",
        source_id=str(rec["ObjectID"]),
        title=title,
        image_url=image_url,
        image_urls_extra=[],
        year_start=int(y0),
        year_end=int(y1),
        lat=g.lat,
        lng=g.lng,
        geo_confidence=g.confidence,
        geo_display=g.display,
        geo_qualifier=g.qualifier,
        medium=rec.get("Medium") or "",
        culture_display=rec.get("Culture") or rec.get("DateText") or "",
        artist_display=rec.get("Creators") or "",
        reveal_text=desc,
        reveal_text_license="CC0" if desc else "",
        credit=(rec.get("CreditLine") or "").strip(),
        object_url=rec.get("ResourceURL") or "",
        is_highlight=False,
        department=rec.get("MuseumLocation") or "",
        classification=rec.get("Classification") or "",
        tags=[k for k in (rec.get("Keywords") or "").split("|") if k],
    )


# ---------------- live fetch (run on your machine) ----------------

def _fetch_csv_rows(url: str):
    with urllib.request.urlopen(url, timeout=60) as r:
        text = r.read().decode("utf-8", errors="replace")
    return csv.DictReader(io.StringIO(text))


def iter_records(limit: int | None = None):
    """Downloads both CSVs once, joins media onto art rows by ObjectID."""
    image_by_object: dict[str, str] = {}
    for row in _fetch_csv_rows(MEDIA_CSV_URL):
        oid = row.get("ObjectID")
        if not oid or not row.get("ImageURL"):
            continue
        if row.get("IsPrimary") == "1" or oid not in image_by_object:
            image_by_object[oid] = row["ImageURL"]

    fetched = 0
    for row in _fetch_csv_rows(ART_CSV_URL):
        row["_image_url"] = image_by_object.get(row.get("ObjectID") or "", "")
        yield row
        fetched += 1
        if limit and fetched >= limit:
            return
