"""Geography resolution.

Museums encode origin wildly differently. Adapters pass an ORDERED list of
candidate strings (most precise first); this module returns the first one it
can resolve to coordinates, with a confidence level.

Resolution order per candidate string:
  1. exact gazetteer hit (site or country/culture)
  2. token scan — any gazetteer key appearing inside the string
     (handles "Spain or Northern Italy, mid 16th century" → Spain, flagged)

The built-in gazetteer covers the countries/cultures that dominate the Met,
CMA and AIC collections. Unresolved strings are logged to `misses` so you can
grow the gazetteer iteratively — expect to add ~50 entries after the first
full ingest. For long-tail precision, plug a real geocoder into
`external_geocode` (left as a no-op hook here).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

# (lat, lng, confidence, display)
# Confidence here is the BEST confidence this entry can grant.
GAZETTEER: dict[str, tuple[float, float, str, str]] = {
    # ---- Archaeological sites / cities (confidence: site) ----
    "meir": (27.42, 30.72, "site", "Meir, Egypt"),
    "thebes": (25.72, 32.61, "site", "Thebes, Egypt"),
    "saqqara": (29.87, 31.22, "site", "Saqqara, Egypt"),
    "deir el-bahri": (25.74, 32.61, "site", "Deir el-Bahri, Egypt"),
    "nineveh": (36.36, 43.15, "site", "Nineveh, Iraq"),
    "nimrud": (36.10, 43.33, "site", "Nimrud, Iraq"),
    "babylon": (32.54, 44.42, "site", "Babylon, Iraq"),
    "ur": (30.96, 46.10, "site", "Ur, Iraq"),
    "persepolis": (29.93, 52.89, "site", "Persepolis, Iran"),
    "athens": (37.98, 23.73, "site", "Athens, Greece"),
    "attica": (38.05, 23.80, "region", "Attica, Greece"),
    "corinth": (37.91, 22.88, "site", "Corinth, Greece"),
    "rome": (41.89, 12.49, "site", "Rome, Italy"),
    "pompeii": (40.75, 14.49, "site", "Pompeii, Italy"),
    "kyoto": (35.01, 135.77, "site", "Kyoto, Japan"),
    "edo": (35.68, 139.77, "site", "Edo (Tokyo), Japan"),
    "jingdezhen": (29.27, 117.18, "site", "Jingdezhen, China"),
    "jiaxing": (30.75, 120.76, "site", "Jiaxing, China"),
    "isfahan": (32.65, 51.67, "site", "Isfahan, Iran"),
    "istanbul": (41.01, 28.98, "site", "Istanbul, Türkiye"),
    "constantinople": (41.01, 28.98, "site", "Constantinople (Istanbul)"),
    "paris": (48.86, 2.35, "site", "Paris, France"),
    "london": (51.51, -0.13, "site", "London, England"),
    "florence": (43.77, 11.26, "site", "Florence, Italy"),
    "venice": (45.44, 12.32, "site", "Venice, Italy"),
    "delft": (52.01, 4.36, "site", "Delft, Netherlands"),
    "amsterdam": (52.37, 4.90, "site", "Amsterdam, Netherlands"),
    "new york": (40.71, -74.01, "site", "New York, United States"),
    "philadelphia": (39.95, -75.17, "site", "Philadelphia, United States"),
    "boston": (42.36, -71.06, "site", "Boston, United States"),
    "chicago": (41.88, -87.63, "site", "Chicago, United States"),
    "new orleans": (29.95, -90.07, "site", "New Orleans, United States"),
    "vienna": (48.21, 16.37, "site", "Vienna, Austria"),
    "meissen": (51.16, 13.47, "site", "Meissen, Germany"),
    "sèvres": (48.82, 2.21, "site", "Sèvres, France"),
    "limoges": (45.83, 1.26, "site", "Limoges, France"),
    "bruges": (51.21, 3.22, "site", "Bruges, Belgium"),
    "benin city": (6.34, 5.63, "site", "Benin City, Nigeria"),
    "cusco": (-13.53, -71.97, "site", "Cusco, Peru"),
    "teotihuacan": (19.69, -98.84, "site", "Teotihuacan, Mexico"),

    # ---- Countries / broad regions (confidence: country) ----
    "egypt": (26.82, 30.80, "country", "Egypt"),
    "greece": (39.07, 21.82, "country", "Greece"),
    "italy": (42.50, 12.50, "country", "Italy"),
    "france": (46.60, 2.30, "country", "France"),
    "england": (52.50, -1.50, "country", "England"),
    "britain": (52.50, -1.50, "country", "Britain"),
    "united kingdom": (52.50, -1.50, "country", "United Kingdom"),
    "scotland": (56.50, -4.00, "country", "Scotland"),
    "ireland": (53.30, -8.00, "country", "Ireland"),
    "spain": (40.20, -3.70, "country", "Spain"),
    "portugal": (39.60, -8.00, "country", "Portugal"),
    "germany": (51.10, 10.40, "country", "Germany"),
    "netherlands": (52.20, 5.50, "country", "Netherlands"),
    "holland": (52.20, 5.50, "country", "Netherlands"),
    "belgium": (50.60, 4.60, "country", "Belgium"),
    "flanders": (51.00, 3.80, "region", "Flanders"),
    "netherlandish": (51.00, 4.50, "region", "The Low Countries"),
    "austria": (47.60, 14.10, "country", "Austria"),
    "switzerland": (46.80, 8.20, "country", "Switzerland"),
    "denmark": (56.00, 10.00, "country", "Denmark"),
    "sweden": (60.10, 15.00, "country", "Sweden"),
    "norway": (61.00, 9.00, "country", "Norway"),
    "russia": (55.75, 37.62, "country", "Russia"),
    "poland": (52.10, 19.40, "country", "Poland"),
    "hungary": (47.20, 19.50, "country", "Hungary"),
    "bohemia": (49.80, 15.00, "region", "Bohemia (Czechia)"),
    "czech": (49.80, 15.00, "country", "Czechia"),
    "türkiye": (39.00, 35.00, "country", "Türkiye"),
    "turkey": (39.00, 35.00, "country", "Türkiye"),
    "iran": (32.40, 53.70, "country", "Iran"),
    "persia": (32.40, 53.70, "culture", "Persia (Iran)"),
    "iraq": (33.10, 43.70, "country", "Iraq"),
    "syria": (35.00, 38.50, "country", "Syria"),
    "lebanon": (33.90, 35.90, "country", "Lebanon"),
    "israel": (31.40, 35.00, "country", "Israel"),
    "jordan": (31.20, 36.50, "country", "Jordan"),
    "saudi arabia": (24.00, 45.00, "country", "Saudi Arabia"),
    "yemen": (15.50, 47.50, "country", "Yemen"),
    "india": (22.50, 79.00, "country", "India"),
    "pakistan": (30.00, 69.30, "country", "Pakistan"),
    "afghanistan": (33.90, 66.00, "country", "Afghanistan"),
    "nepal": (28.20, 84.10, "country", "Nepal"),
    "tibet": (31.50, 88.00, "region", "Tibet"),
    "sri lanka": (7.60, 80.70, "country", "Sri Lanka"),
    "china": (34.70, 104.10, "country", "China"),
    "japan": (36.50, 138.00, "country", "Japan"),
    "korea": (36.60, 127.90, "country", "Korea"),
    "vietnam": (16.00, 107.80, "country", "Vietnam"),
    "thailand": (15.10, 101.00, "country", "Thailand"),
    "cambodia": (12.60, 104.90, "country", "Cambodia"),
    "myanmar": (21.20, 96.50, "country", "Myanmar"),
    "burma": (21.20, 96.50, "country", "Myanmar (Burma)"),
    "indonesia": (-2.20, 117.40, "country", "Indonesia"),
    "java": (-7.50, 110.00, "region", "Java, Indonesia"),
    "philippines": (12.90, 122.00, "country", "Philippines"),
    "mongolia": (46.90, 103.10, "country", "Mongolia"),
    "nigeria": (9.10, 8.70, "country", "Nigeria"),
    "mali": (17.60, -4.00, "country", "Mali"),
    "ghana": (7.90, -1.20, "country", "Ghana"),
    "côte d'ivoire": (7.50, -5.50, "country", "Côte d'Ivoire"),
    "ivory coast": (7.50, -5.50, "country", "Côte d'Ivoire"),
    "cameroon": (5.70, 12.70, "country", "Cameroon"),
    "congo": (-2.90, 23.60, "country", "DR Congo"),
    "ethiopia": (9.10, 40.50, "country", "Ethiopia"),
    "kenya": (0.20, 37.90, "country", "Kenya"),
    "tanzania": (-6.40, 34.90, "country", "Tanzania"),
    "south africa": (-29.00, 25.00, "country", "South Africa"),
    "morocco": (31.80, -7.10, "country", "Morocco"),
    "tunisia": (34.10, 9.60, "country", "Tunisia"),
    "algeria": (28.00, 2.60, "country", "Algeria"),
    "sudan": (15.60, 30.20, "country", "Sudan"),
    "nubia": (21.50, 31.00, "culture", "Nubia (Sudan/Egypt)"),
    "united states": (39.80, -98.60, "country", "United States"),
    "american": (39.80, -98.60, "country", "United States"),
    "canada": (56.10, -106.30, "country", "Canada"),
    "mexico": (23.60, -102.60, "country", "Mexico"),
    "guatemala": (15.80, -90.20, "country", "Guatemala"),
    "peru": (-9.20, -75.00, "country", "Peru"),
    "bolivia": (-16.30, -63.60, "country", "Bolivia"),
    "colombia": (4.60, -74.30, "country", "Colombia"),
    "ecuador": (-1.80, -78.20, "country", "Ecuador"),
    "brazil": (-14.20, -51.90, "country", "Brazil"),
    "chile": (-35.70, -71.50, "country", "Chile"),
    "argentina": (-38.40, -63.60, "country", "Argentina"),
    "australia": (-25.30, 133.80, "country", "Australia"),
    "new zealand": (-41.80, 172.80, "country", "New Zealand"),
    "papua new guinea": (-6.30, 143.90, "country", "Papua New Guinea"),
    "fiji": (-17.70, 178.00, "country", "Fiji"),
    "hawaii": (20.80, -156.30, "region", "Hawai'i"),

    # ---- Cultures with no modern-country name (confidence: culture) ----
    "byzantine": (41.01, 28.98, "culture", "Byzantine Empire"),
    "roman": (41.89, 12.49, "culture", "Roman"),
    "etruscan": (42.40, 11.90, "culture", "Etruscan (Italy)"),
    "greek": (39.07, 21.82, "culture", "Greek"),
    "cypriot": (35.10, 33.20, "culture", "Cyprus"),
    "minoan": (35.30, 25.10, "culture", "Minoan (Crete)"),
    "mycenaean": (37.73, 22.76, "culture", "Mycenaean (Greece)"),
    "egyptian": (26.82, 30.80, "culture", "Egypt"),
    "assyrian": (36.36, 43.15, "culture", "Assyria (Iraq)"),
    "babylonian": (32.54, 44.42, "culture", "Babylonia (Iraq)"),
    "sumerian": (31.00, 46.10, "culture", "Sumer (Iraq)"),
    "achaemenid": (29.93, 52.89, "culture", "Achaemenid Persia"),
    "sasanian": (33.10, 44.60, "culture", "Sasanian Persia"),
    "parthian": (35.00, 51.00, "culture", "Parthia (Iran)"),
    "scythian": (48.00, 45.00, "culture", "Scythian (Eurasian steppe)"),
    "celtic": (48.50, 7.00, "culture", "Celtic Europe"),
    "viking": (59.00, 10.00, "culture", "Viking Scandinavia"),
    "ottoman": (39.00, 35.00, "culture", "Ottoman Empire"),
    "mughal": (27.18, 78.02, "culture", "Mughal India"),
    "safavid": (32.65, 51.67, "culture", "Safavid Iran"),
    "timurid": (39.65, 66.96, "culture", "Timurid (Central Asia)"),
    "maya": (16.80, -89.80, "culture", "Maya (Mesoamerica)"),
    "aztec": (19.43, -99.13, "culture", "Aztec (Mexico)"),
    "mexica": (19.43, -99.13, "culture", "Mexica/Aztec (Mexico)"),
    "olmec": (18.00, -94.60, "culture", "Olmec (Mexico)"),
    "zapotec": (17.00, -96.70, "culture", "Zapotec (Mexico)"),
    "mixtec": (17.50, -97.50, "culture", "Mixtec (Mexico)"),
    "inca": (-13.53, -71.97, "culture", "Inca (Peru)"),
    "moche": (-8.10, -79.00, "culture", "Moche (Peru)"),
    "nazca": (-14.80, -75.10, "culture", "Nazca (Peru)"),
    "chimú": (-8.10, -79.10, "culture", "Chimú (Peru)"),
    "wari": (-13.10, -74.20, "culture", "Wari (Peru)"),
    "edo peoples": (6.34, 5.63, "culture", "Edo peoples (Nigeria)"),
    "yoruba": (7.80, 4.50, "culture", "Yoruba (Nigeria)"),
    "akan": (6.70, -1.60, "culture", "Akan (Ghana)"),
    "kongo": (-5.30, 14.40, "culture", "Kongo (Central Africa)"),
    "luba": (-8.00, 26.00, "culture", "Luba (DR Congo)"),
    "dogon": (14.40, -3.40, "culture", "Dogon (Mali)"),
    "bamana": (13.00, -7.00, "culture", "Bamana (Mali)"),
    "fang": (1.50, 11.50, "culture", "Fang (Gabon/Cameroon)"),
    "maori": (-38.00, 176.00, "culture", "Māori (New Zealand)"),
    "aboriginal": (-25.30, 133.80, "culture", "Aboriginal Australia"),
}

# Dynasty / period words that imply a place when nothing else resolves.
PERIOD_TO_PLACE: dict[str, str] = {
    "ming": "china", "qing": "china", "tang": "china", "song": "china",
    "han dynasty": "china", "yuan": "china", "shang": "china", "zhou": "china",
    "edo period": "japan", "meiji": "japan", "heian": "japan",
    "muromachi": "japan", "momoyama": "japan", "kamakura": "japan",
    "joseon": "korea", "goryeo": "korea", "silla": "korea",
    "new kingdom": "egypt", "middle kingdom": "egypt", "old kingdom": "egypt",
    "ptolemaic": "egypt", "dynasty 12": "egypt",
    "gupta": "india", "chola": "india",
    "khmer": "cambodia",
}

AMBIGUOUS_SEP = re.compile(r"\bor\b|/|\bpossibly\b|\bprobably\b", re.IGNORECASE)
QUALIFIER_WORDS = re.compile(r"\b(probably|possibly|perhaps|attributed)\b", re.IGNORECASE)


@dataclass
class GeoResult:
    lat: float
    lng: float
    confidence: str      # site | region | country | culture
    display: str
    qualifier: str = ""  # "probably from" etc.
    matched_key: str = ""


class GeoResolver:
    def __init__(self):
        self.misses: dict[str, int] = {}   # unresolved strings -> count

    def resolve(self, candidates: list[str], qualifier: str = "") -> Optional[GeoResult]:
        """Try each candidate string in order; return first resolution."""
        for raw in candidates:
            if not raw or not raw.strip():
                continue
            r = self._resolve_one(raw.strip())
            if r:
                q = qualifier
                if not q and QUALIFIER_WORDS.search(raw):
                    q = "probably from"
                if AMBIGUOUS_SEP.search(raw) and r.confidence in ("site", "region"):
                    # "Spain or Northern Italy" — don't pretend site precision
                    r.confidence = "country"
                r.qualifier = q
                return r
        for raw in candidates:
            if raw and raw.strip():
                self.misses[raw.strip()] = self.misses.get(raw.strip(), 0) + 1
        return None

    def _resolve_one(self, s: str) -> Optional[GeoResult]:
        low = s.lower()

        # 1. exact hit
        if low in GAZETTEER:
            return self._hit(low)

        # 2. longest gazetteer key contained in the string
        #    ("China, Jiaxing, 16th century" → jiaxing beats china)
        best = None
        for key in GAZETTEER:
            if re.search(rf"(?<![a-z]){re.escape(key)}(?![a-z])", low):
                if best is None or self._rank(key) < self._rank(best):
                    best = key
        if best:
            return self._hit(best)

        # 3. period/dynasty implies place
        for period, place in PERIOD_TO_PLACE.items():
            if period in low:
                r = self._hit(place)
                r.confidence = "culture"
                return r

        # 4. hook for a real geocoder (Nominatim etc.) — off by default
        return self.external_geocode(s)

    @staticmethod
    def _rank(key: str) -> int:
        order = {"site": 0, "region": 1, "country": 2, "culture": 3}
        return order[GAZETTEER[key][2]]

    @staticmethod
    def _hit(key: str) -> GeoResult:
        lat, lng, conf, disp = GAZETTEER[key]
        return GeoResult(lat=lat, lng=lng, confidence=conf, display=disp, matched_key=key)

    def external_geocode(self, s: str) -> Optional[GeoResult]:
        """Plug in Nominatim/Google here if the gazetteer isn't enough.
        Deliberately a no-op by default: deterministic, offline, free."""
        return None
