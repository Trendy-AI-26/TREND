from uuid import uuid4

import pytest

from app.models.kit import KitAnswers, ToneEnum


def test_valid_answers():
    answers = KitAnswers(
        tagline="Hello",
        tone=ToneEnum.formal,
        industry="beauty",
        audience="owners",
        colors=["#FF0000"],
        avoid_words="cheap",
    )
    assert answers.industry == "beauty"


def test_product_asset_id_is_preserved():
    product_asset_id = uuid4()
    answers = KitAnswers(product_asset_id=product_asset_id)
    assert answers.product_asset_id == product_asset_id


def test_tagline_too_long():
    with pytest.raises(ValueError):
        KitAnswers(tagline="x" * 161)


def test_audience_too_short():
    with pytest.raises(ValueError):
        KitAnswers(audience="x")


def test_audience_too_long():
    with pytest.raises(ValueError):
        KitAnswers(audience="x" * 501)


def test_too_many_colors():
    with pytest.raises(ValueError):
        KitAnswers(colors=["#FF0000", "#00FF00", "#0000FF", "#FFFFFF"])


def test_invalid_hex_color():
    with pytest.raises(ValueError):
        KitAnswers(colors=["notahex"])


def test_hex_colors_uppercased():
    answers = KitAnswers(colors=["#ff5733"])
    assert answers.colors == ["#FF5733"]


def test_avoid_words_too_long():
    with pytest.raises(ValueError):
        KitAnswers(avoid_words="x" * 501)


def test_empty_strings_become_none():
    answers = KitAnswers(tagline="   ", industry="   ", audience="   ", avoid_words="   ")
    assert answers.tagline is None
    assert answers.industry is None
    assert answers.audience is None
    assert answers.avoid_words is None


def test_industry_too_long():
    with pytest.raises(ValueError):
        KitAnswers(industry="x" * 121)
