# Data sources

Status of museum open-access APIs/dumps as candidate `adapters/*.py` files
(see README → "Adding a museum later"). Originally researched July 2026;
six were built and ingested the same week, so "Built" below reflects actual
integration experience, not just docs-reading. Verify licensing/endpoints
again before re-ingesting — these programs do change (Nasjonalmuseet
retired its v1 API in Jan 2025, Walters' v1 closed in 2023).

## Built and ingested (keyless)

| Source | Adapter | Yield | Notes |
|---|---|---|---|
| **Minneapolis Institute of Art** | `adapters/mia.py` | ~50% | Static JSON dump on GitHub, walked by sequential id off the raw CDN — no API, no rate limit. Images are CC0-adjacent but not blanket CC0 (`restricted`/`rights_type` fields gate it). |
| **Walters Art Museum** | `adapters/walters.py` | ~33% | CSV dump (`art.csv` + `media.csv` joined by ObjectID) — their live API v1 closed in 2023, this *is* the current path. Data and images both CC0. |
| **Statens Museum for Kunst (Denmark)** | `adapters/smk.py` | ~93% | Clean modern REST API, real ISO dates, per-object `public_domain` flag. Best yield of any source here — carries its own Danish-nationality-adjective table since `creator_nationality` is in Danish. |
| **Museums Victoria (Australia)** | `adapters/museums_victoria.py` | ~51% | REST API, `User-Agent` header only. Fixed the Oceania gap the original pool had. Mixes humanities with natural-science specimens — filtered to `recordtype=item`. |
| **Victoria and Albert Museum** | `adapters/vam.py` | ~80% | REST API (OpenAPI spec), two requests per object (search then full record) since there's no bulk dump. Strong design/decorative-arts/fashion coverage. |
| **Smithsonian Open Access** | `adapters/smithsonian.py` | ~60% | Bulk line-delimited JSON on S3, sharded by owning unit — no key, no rate limit at all. Ships with `saam` (American Art), `nmafa` (African Art), and `chndm` (**Cooper Hewitt, Smithsonian Design Museum** — see below) enabled; add more unit codes from the Smithsonian/OpenAccess README to broaden further. |

**Cooper Hewitt turned out not to need its own key-gated adapter** — it's a
Smithsonian unit (`chndm`) and comes for free through `smithsonian.py`.

## Built, needs a key to run

| Source | Adapter | Notes |
|---|---|---|
| **Harvard Art Museums** | `adapters/harvard.py` | Code written and unit-tested against the documented sample record, but untested live — needs a free key (`export HARVARD_API_KEY=...`, instant signup at harvardartmuseums.org/collections/api). Non-commercial use only. |

## Investigated, not built

| Source | Why not |
|---|---|
| **Rijksmuseum** | Looked keyless-simple from docs summaries, but their current data services (Search API, data dumps) are Linked Art / CIDOC-CRM / n-triples (RDF), not flat JSON — meaningfully more parsing work than every adapter above. The old simple REST API (`rijksmuseum.nl/api/en/collection`) needs a key. Worth doing, but budget real time for the RDF. |
| **Getty Museum** | Same shape of problem — the only bulk path is an `activity-stream` of Linked Art JSON-LD objects requiring a follow-up fetch per object plus CIDOC-CRM-style parsing. |
| **Brooklyn Museum** | Docs site is behind a JS/bot-protection challenge that couldn't be scraped for real field examples, and the API itself needs a key — didn't want to ship a field-mapping guess with nothing to verify it against. |

## Bigger investment, still noteworthy

| Source | Why it's different | Effort |
|---|---|---|
| **Wikidata / Wikimedia Commons SPARQL** | Uniquely gives real `coordinate location` and `inception date` **properties** directly via SPARQL for many artworks, instead of the free-text place strings every museum API above requires `geo.py` to resolve. Could raise `geo_confidence` to `"site"` for far more objects than our gazetteer cascade manages today. Per-image license varies (check Commons file license). | High |
| **Europeana** | Aggregates 4,000+ European institutions, tens of millions of items — the single biggest diversity win on this list, but every contributing institution's metadata shape differs, so `normalize()` needs to handle a much messier `rec` than any adapter here does today. | High |
| **DigitaltMuseum / Nasjonalmuseet (Norway + Sweden)** | 3.86M objects across 174 Norwegian + 51 Swedish museums via one API. Key request is a manual/email step through KulturIT, not instant self-serve. | Medium |
| **DPLA (Digital Public Library of America)** | 15M+ items from US libraries/museums/archives (key required). Heavy overlap risk with sources already ingested (Met, Smithsonian) via re-published records — needs dedupe-aware filtering beyond the existing `source:id` uid scheme. | High |
| **POP / Ministère de la Culture (France)** | France's national aggregator (Musée d'Orsay, Louvre-adjacent collections, "Joconde" database) — keyless bulk download via data.culture.gouv.fr. Metadata is in French — dates/places need French-aware parsing before hitting `geo.py`. | Medium-high |
| **British Museum** | SPARQL/CIDOC-CRM endpoint only, and the museum's own search results flag it as inconsistently maintained/unreliable. Only worth it if nothing else needs 3M+ objects badly enough to justify the RDF parsing. | High, uncertain payoff |

## What matters when adding one

CC0/public-domain (or at least CC-BY, like AIC's `reveal_text`) so the
reveal screen's attribution rule stays simple; a real `year_start`/
`year_end` or an unambiguous date string; a resolvable place string (or
real lat/lng) for `geo.py`; and — as the RDF sources above show — actually
fetching a sample record before assuming a docs summary tells you the true
integration cost.
