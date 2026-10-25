from app.services.kit_summary import derive_status, derive_summary, KitStatusEnum


def test_derive_status_not_started_when_all_none():
    assert derive_status(tagline=None, audience=None, colors=[], avoid_words=None, industry=None) == KitStatusEnum.not_started


def test_derive_status_complete_when_required_fields_present():
    assert derive_status(tagline=None, industry="beauty", audience="owners", colors=["#FF0000"], avoid_words=None) == KitStatusEnum.complete


def test_derive_status_in_progress_when_only_tagline():
    assert derive_status(tagline="hi", industry=None, audience=None, colors=[], avoid_words=None) == KitStatusEnum.in_progress


def test_derive_status_in_progress_when_missing_colors():
    assert derive_status(tagline=None, industry="beauty", audience="aa", colors=[], avoid_words=None) == KitStatusEnum.in_progress


def test_derive_status_in_progress_when_industry_is_missing():
    assert derive_status(tagline=None, industry=None, audience="owners", colors=["#FF0000"], avoid_words=None) == KitStatusEnum.in_progress


def test_derive_status_in_progress_when_only_avoid_words():
    assert derive_status(tagline=None, industry=None, audience=None, colors=[], avoid_words="neon") == KitStatusEnum.in_progress


def test_derive_summary_returns_none_when_not_started():
    result = derive_summary(brand_name="Acme", tagline=None, audience=None, colors=[], avoid_words=None, industry=None)
    assert result is None


def test_derive_summary_contains_brand_name():
    result = derive_summary(brand_name="Acme", tagline="Hello", industry="beauty", audience="owners", colors=["#FF0000"], avoid_words=None)
    assert "Acme" in result


def test_derive_summary_uses_none_specified_for_missing_optionals():
    result = derive_summary(brand_name="Acme", tagline=None, industry="beauty", audience="owners", colors=["#FF0000"], avoid_words=None)
    assert "Tagline: None specified" in result


def test_derive_summary_joins_colors_with_comma():
    result = derive_summary(brand_name="Acme", tagline=None, industry="beauty", audience="owners", colors=["#FF0000", "#00FF00"], avoid_words=None)
    assert "#FF0000, #00FF00" in result


def test_derive_summary_is_deterministic():
    result1 = derive_summary(brand_name="Acme", tagline="Hello", industry="beauty", audience="owners", colors=["#FF0000"], avoid_words="cheap")
    result2 = derive_summary(brand_name="Acme", tagline="Hello", industry="beauty", audience="owners", colors=["#FF0000"], avoid_words="cheap")
    assert result1 == result2
    assert result1 is not None


def test_derive_summary_format_line_order():
    result = derive_summary(brand_name="Acme", tagline="Hello", industry="beauty", audience="owners", colors=["#FF0000"], avoid_words="cheap")
    lines = result.split("\n")
    assert len(lines) == 6
    assert lines[0].startswith("Brand: ")
    assert lines[1].startswith("Tagline: ")
    assert lines[2].startswith("Industry: ")
    assert lines[3].startswith("Audience: ")
    assert lines[4].startswith("Colors: ")
    assert lines[5].startswith("Avoid: ")


def test_derive_summary_includes_industry():
    result = derive_summary(brand_name="Acme", tagline=None, industry="beauty", audience=None, colors=[], avoid_words=None)
    assert result is not None and "Industry: beauty" in result
