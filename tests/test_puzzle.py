import math

import pytest

import puzzle


# ---------------- timeline ----------------

@pytest.mark.parametrize(
    "year,expected_block",
    [
        (-3000, 0),
        (-2751, 0),
        (-2750, 1),
        (1999, 19),
        (2000, 19),   # clamps at the final block
        (2500, 19),   # anything past 2000 CE also clamps
        (-4000, 0),   # anything before 3000 BCE clamps to the first block
    ],
)
def test_block_of(year, expected_block):
    assert puzzle.block_of(year) == expected_block


def test_block_label_first_and_last():
    assert puzzle.block_label(0) == "3000 BCE – 2750 BCE"
    assert puzzle.block_label(19) == "1750 CE – 2000 CE"


def test_block_label_crosses_bce_ce_boundary():
    # Block 11 spans 250 BCE to 0 CE.
    assert puzzle.block_label(11) == "250 BCE – 0 CE"


# ---------------- scoring ----------------

def test_geo_score_zero_distance_is_max():
    assert puzzle.geo_score(30.0, 40.0, 30.0, 40.0) == puzzle.MAX_GEO


def test_geo_score_decays_with_distance():
    near = puzzle.geo_score(0, 0, 0, 1)
    far = puzzle.geo_score(0, 0, 0, 90)
    assert puzzle.MAX_GEO > near > far > 0


def test_geo_score_known_value():
    # Along the equator, great-circle distance is exactly R * delta-longitude
    # (in radians), so we can construct a point exactly GEO_DECAY_KM away and
    # confirm the score lands at exactly 1/e of max.
    r = 6371.0
    lng2 = math.degrees(puzzle.GEO_DECAY_KM / r)
    score = puzzle.geo_score(0, 0, 0, lng2)
    assert score == round(puzzle.MAX_GEO * math.exp(-1))


def test_time_score_full_credit_when_overlapping():
    lo = puzzle.block_of(-2060)
    hi = puzzle.block_of(-2040)
    assert lo == hi
    assert puzzle.time_score(lo, -2060, -2040) == puzzle.MAX_TIME


def test_time_score_decays_symmetrically_around_range():
    lo = puzzle.block_of(-2060)
    before = puzzle.time_score(lo - 2, -2060, -2040)
    after = puzzle.time_score(lo + 2, -2060, -2040)
    assert before == after


def test_time_score_known_value_one_block_off():
    lo = puzzle.block_of(-2060)
    score = puzzle.time_score(lo - 1, -2060, -2040)
    assert score == round(puzzle.MAX_TIME * math.exp(-1 / puzzle.TIME_DECAY_BLOCKS))


def test_round_score_sums_geo_and_time():
    guess = {"lat": 30.96, "lng": 46.10, "block": puzzle.block_of(-2060)}
    artifact = {"lat": 30.96, "lng": 46.10, "year_start": -2060, "year_end": -2040}
    result = puzzle.round_score(guess, artifact)
    assert result == {"geo": puzzle.MAX_GEO, "time": puzzle.MAX_TIME, "total": puzzle.MAX_GEO + puzzle.MAX_TIME}


# ---------------- share card ----------------

@pytest.mark.parametrize(
    "total,expected_emoji",
    [(10000, "🟩"), (9000, "🟩"), (8999, "🟦"), (7000, "🟦"), (6999, "🟨"), (5000, "🟨"), (4999, "🟥"), (0, "🟥")],
)
def test_share_emoji_thresholds(total, expected_emoji):
    assert puzzle.share_emoji(total) == expected_emoji


def test_share_card_format():
    card = puzzle.share_card("2026-07-07", [9500, 6000, 100])
    assert card == "2026-07-07\n🟩🟨🟥 15,600"


# ---------------- continent bucketing ----------------

@pytest.mark.parametrize(
    "lat,lng,expected",
    [
        (-33.87, 151.21, "oceania"),   # Sydney
        (40.71, -74.01, "americas"),   # New York
        (30.04, 31.24, "africa"),      # Cairo
        (35.68, 139.69, "asia"),       # Tokyo
        (24.71, 46.68, "middle_east"), # Riyadh
        (48.86, 2.35, "europe"),       # Paris
    ],
)
def test_continent_of(lat, lng, expected):
    assert puzzle.continent_of(lat, lng) == expected


# ---------------- daily selection ----------------

def make_pool(n, source="met", continent_lat=48.0, continent_lng=2.0, year=1500):
    return [
        {
            "source": source,
            "source_id": str(i),
            "lat": continent_lat,
            "lng": continent_lng,
            "year_start": year,
            "year_end": year,
        }
        for i in range(n)
    ]


def test_select_daily_is_deterministic_for_same_seed():
    pool = make_pool(50)
    a = puzzle.select_daily(pool, "daily-2026-07-07")
    b = puzzle.select_daily(pool, "daily-2026-07-07")
    assert [x["source_id"] for x in a] == [x["source_id"] for x in b]


def test_select_daily_different_seeds_can_differ():
    pool = make_pool(50)
    a = puzzle.select_daily(pool, "daily-2026-07-07")
    b = puzzle.select_daily(pool, "daily-2026-07-08")
    assert [x["source_id"] for x in a] != [x["source_id"] for x in b]


def test_select_daily_respects_caps_with_diverse_pool():
    # One continent/source/era per item won't satisfy caps if the pool is
    # homogeneous, so give it enough spread to hit the requested count
    # without relaxing.
    pool = []
    continents = [(-33, 151), (40, -74), (30, 31), (35, 139), (24, 46), (48, 2)]
    for i in range(30):
        lat, lng = continents[i % len(continents)]
        pool.append(
            {
                "source": ["met", "cleveland", "aic"][i % 3],
                "source_id": str(i),
                "lat": lat,
                "lng": lng,
                "year_start": 1000 + (i % 6) * 300,
                "year_end": 1000 + (i % 6) * 300,
            }
        )
    picked = puzzle.select_daily(pool, "seed", n=10, max_per_continent=3, max_per_source=5, max_per_era=3)
    assert len(picked) == 10

    by_cont: dict[str, int] = {}
    for a in picked:
        cont = puzzle.continent_of(a["lat"], a["lng"])
        by_cont[cont] = by_cont.get(cont, 0) + 1
    assert max(by_cont.values()) <= 3


def test_select_daily_best_effort_on_small_pool():
    pool = make_pool(3)
    picked = puzzle.select_daily(pool, "seed", n=10)
    assert len(picked) == 3


def test_select_daily_relaxes_caps_for_homogeneous_pool():
    # All 10 items share one continent/source/era, so the per-continent cap
    # (the tightest one here) governs. It relaxes across 3 attempts —
    # 3, then 4, then 5 — and best-effort-returns at 5 without ever
    # reaching the requested n=10, since relaxation is capped at 3 tries.
    pool = make_pool(10)
    picked = puzzle.select_daily(pool, "seed", n=10, max_per_continent=3, max_per_source=5, max_per_era=3)
    assert len(picked) == 5
