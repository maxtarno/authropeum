import json
import os

from adapters import met
from geo import GeoResolver
from pipeline import run


FIXTURES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fixtures")


def load_fixture(name):
    with open(os.path.join(FIXTURES_DIR, f"{name}.json")) as f:
        return json.load(f)


def test_run_accepts_bundled_met_fixtures():
    records = load_fixture("met")
    pool, rejects = {}, []
    ok, bad = run(records, met, GeoResolver(), pool, rejects)

    assert ok > 0
    assert ok == len(pool)
    assert ok + bad == len(records)
    for art in pool.values():
        assert art["source"] == "met"
        assert art["image_url"]


def test_run_dedupes_by_source_and_id():
    records = load_fixture("met")
    pool, rejects = {}, []
    run(records, met, GeoResolver(), pool, rejects)
    size_after_first = len(pool)

    # Re-running the same records (as an incremental re-ingest would) should
    # update in place, not duplicate.
    run(records, met, GeoResolver(), pool, rejects)
    assert len(pool) == size_after_first


def test_run_records_rejects_for_bad_input():
    bad_record = {"objectID": "999999", "title": ""}  # will fail schema validation
    pool, rejects = {}, []
    ok, bad = run([bad_record], met, GeoResolver(), pool, rejects)

    assert ok == 0
    assert bad == 1
    assert len(rejects) == 1
    assert "999999" in rejects[0]
