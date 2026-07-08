import pytest

from schema import Artifact, RejectRecord, validate


def make_artifact(**overrides) -> Artifact:
    defaults = dict(
        source="met",
        source_id="1",
        title="Cuneiform Tablet",
        image_url="https://images.metmuseum.org/x.jpg",
        year_start=-2060,
        year_end=-2040,
        lat=30.96,
        lng=46.10,
        geo_confidence="site",
        geo_display="Ur, Iraq",
    )
    defaults.update(overrides)
    return Artifact(**defaults)


def test_valid_artifact_passes():
    art = make_artifact()
    assert validate(art) is art


@pytest.mark.parametrize(
    "overrides,expected_reason_substr",
    [
        ({"title": ""}, "missing title"),
        ({"title": "   "}, "missing title"),
        ({"image_url": ""}, "missing image"),
        ({"year_start": 0, "year_end": 0}, "missing dates"),
        ({"year_start": 100, "year_end": 50}, "inverted date range"),
        ({"year_end": 3000}, "in the future"),
        ({"year_start": -3500}, "predates timeline"),
        ({"year_start": -2060, "year_end": -1000}, "too wide"),
        ({"lat": 0.0, "lng": 0.0}, "unresolved geography"),
        ({"geo_confidence": "planet"}, "bad geo_confidence"),
        ({"geo_display": ""}, "missing geo_display"),
    ],
)
def test_validate_rejects(overrides, expected_reason_substr):
    art = make_artifact(**overrides)
    with pytest.raises(RejectRecord) as exc_info:
        validate(art)
    assert expected_reason_substr in exc_info.value.reason


def test_validate_allows_max_range_boundary():
    # exactly at the default 700y cap should pass; one year over should not.
    art = make_artifact(year_start=-1000, year_end=-300)
    assert validate(art) is art

    art_too_wide = make_artifact(year_start=-1000, year_end=-299)
    with pytest.raises(RejectRecord):
        validate(art_too_wide)


def test_uid_combines_source_and_id():
    art = make_artifact(source="cleveland", source_id="42")
    assert art.uid == "cleveland:42"
