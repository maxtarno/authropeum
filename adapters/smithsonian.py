"""Adapter: Smithsonian Open Access.

Data: https://registry.opendata.aws/smithsonian-open-access/ — no key, no
      rate limit. Metadata is sharded by owning unit (SAAM = American Art
      Museum, NMAfA = African Art Museum, ...) into 256 hash-bucketed
      line-delimited-JSON files each, indexed at
      metadata/edan/{unit}/index.txt (lowercase unit code).

We start with SAAM and NMAfA (`UNITS` below) since both are art museums
with rich date/geography metadata; add more Smithsonian unit codes from
the README at github.com/Smithsonian/OpenAccess to broaden further.

Fields worth knowing:
  * `content.descriptiveNonRepeating.online_media.media[]` — image list;
    each has its own `usage.access` (CC0 or not) independent of the object.
  * `content.indexedStructured.date` — free-ish year strings ("1860s").
  * `content.indexedStructured.geoLocation[]` — structured
    Continent/Country/State, when present; falls back to
    `content.indexedStructured.place[]` free-text otherwise.
  * `content.descriptiveNonRepeating.metadata_usage.access` — CC0 gate for
    the record as a whole.
"""

from __future__ import annotations

import json
import re
import time
import urllib.request

from schema import Artifact, RejectRecord
from geo import GeoResolver

UNITS = ["saam", "nmafa", "chndm"]  # chndm = Cooper Hewitt, Smithsonian Design Museum
INDEX_URL = "https://smithsonian-open-access.s3-us-west-2.amazonaws.com/metadata/edan/{unit}/index.txt"

# Pairs each number with an adjacent era marker so "100 B.C.-100 A.D."
# doesn't collapse to (100, 100) — a plain digit-only regex would lose the
# BCE/CE distinction entirely and silently produce a wrong-signed year.
_YEAR_WITH_ERA_RE = re.compile(
    r"(\d{1,4})\s*(b\.?\s?c\.?\s?e?\.?|a\.?\s?d\.?|c\.?\s?e\.?)?", re.IGNORECASE
)
_CENTURY_RE = re.compile(r"(\d{1,2})(?:st|nd|rd|th)\s+century\s*(b\.?\s?c\.?\s?e?\.?)?", re.IGNORECASE)


def _parse_years(strs: list[str]) -> tuple[int, int] | tuple[None, None]:
    for s in strs or []:
        if not s or not s.strip():
            continue

        m = _CENTURY_RE.search(s)
        if m:
            century = int(m.group(1))
            is_bce = bool(m.group(2))
            y0, y1 = (century - 1) * 100, century * 100
            return (-y1, -y0) if is_bce else (y0, y1)

        years = []
        for num_str, era in _YEAR_WITH_ERA_RE.findall(s):
            if not num_str:
                continue
            num = int(num_str)
            if era and era.lower().replace(".", "").replace(" ", "").startswith("b"):
                num = -num
            years.append(num)
        if years:
            return min(years), max(years)

    return None, None


def _geo_candidates(indexed: dict) -> list[str]:
    candidates = []
    for loc in indexed.get("geoLocation") or []:
        if not isinstance(loc, dict):
            continue
        for level in ("L3", "L2", "L1"):  # most specific first
            entry = loc.get(level)
            if isinstance(entry, dict) and entry.get("content"):
                candidates.append(entry["content"])
    candidates += [p for p in (indexed.get("place") or []) if isinstance(p, str)]
    return candidates


def normalize(rec: dict, geo: GeoResolver) -> Artifact:
    content = rec.get("content") or {}
    non_repeating = content.get("descriptiveNonRepeating") or {}
    indexed = content.get("indexedStructured") or {}
    freetext = content.get("freetext") or {}

    if (non_repeating.get("metadata_usage") or {}).get("access") != "CC0":
        raise RejectRecord("not CC0")

    media = (non_repeating.get("online_media") or {}).get("media") or []
    image_url = ""
    for m in media:
        if m.get("type") == "Images" and (m.get("usage") or {}).get("access") == "CC0" and m.get("content"):
            image_url = m["content"]
            break
    if not image_url:
        raise RejectRecord("no CC0 image")

    date_strs = indexed.get("date") or [d.get("content", "") for d in freetext.get("date") or []]
    year_start, year_end = _parse_years(date_strs)
    if year_start is None:
        raise RejectRecord(f"unparseable date: {date_strs!r}")

    candidates = _geo_candidates(indexed)
    unit_code = non_repeating.get("unit_code") or ""
    if unit_code == "SAAM":
        # American Art Museum — country-level "United States" is a safe
        # last-resort default for a museum scoped to American art, when no
        # more specific place tag exists at all.
        candidates = candidates + ["united states"]
    g = geo.resolve(candidates)
    if g is None:
        raise RejectRecord(f"geo unresolved: {candidates}")

    title = non_repeating.get("title", {}).get("content") or rec.get("title") or ""
    if not title.strip():
        raise RejectRecord("missing title")

    names = freetext.get("name") or []
    artist_display = "; ".join(n.get("content", "") for n in names if n.get("content"))

    physical = freetext.get("physicalDescription") or []
    medium = next((p.get("content", "") for p in physical if p.get("label") == "Medium"), "")

    credit_lines = freetext.get("creditLine") or []
    credit = credit_lines[0].get("content", "") if credit_lines else ""

    object_types = freetext.get("objectType") or indexed.get("object_type") or []
    classification = object_types[0] if isinstance(object_types, list) and object_types else (
        object_types[0].get("content", "") if object_types else ""
    )

    return Artifact(
        source="smithsonian",
        source_id=non_repeating.get("record_ID") or rec.get("url") or "",
        title=title,
        image_url=image_url,
        image_urls_extra=[m["content"] for m in media[1:3] if m.get("content")],
        year_start=year_start,
        year_end=year_end,
        lat=g.lat,
        lng=g.lng,
        geo_confidence=g.confidence,
        geo_display=g.display,
        geo_qualifier=g.qualifier,
        medium=medium,
        culture_display=(indexed.get("topic") or [""])[0] if indexed.get("topic") else "",
        artist_display=artist_display,
        reveal_text="",
        reveal_text_license="",
        credit=credit,
        object_url=non_repeating.get("record_link") or "",
        is_highlight=False,
        department=non_repeating.get("unit_code") or rec.get("unitCode") or "",
        classification=classification if isinstance(classification, str) else "",
        tags=(indexed.get("topic") or [])[:8],
    )


# ---------------- live fetch (run on your machine) ----------------

def iter_records(limit: int | None = None, units: list[str] | None = None, sleep: float = 0.05):
    """Streams each unit's hash-sharded line-delimited JSON files in order."""
    fetched = 0
    for unit in units or UNITS:
        with urllib.request.urlopen(INDEX_URL.format(unit=unit), timeout=30) as r:
            shard_urls = [line.strip() for line in r.read().decode().splitlines() if line.strip()]
        for shard_url in shard_urls:
            try:
                with urllib.request.urlopen(shard_url, timeout=30) as r:
                    text = r.read().decode("utf-8", errors="replace")
            except Exception:
                continue
            for line in text.splitlines():
                if not line.strip():
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue
                fetched += 1
                if limit and fetched >= limit:
                    return
            time.sleep(sleep)
