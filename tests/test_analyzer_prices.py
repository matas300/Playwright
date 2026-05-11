import pytest
from src.analyzer.prices import extract_price


@pytest.mark.parametrize("text,expected", [
    ("Nuomoju butą už 580 eur/mėn", 580),
    ("Kaina: 600€", 600),
    ("Price 650 EUR per month", 650),
    ("Nuomos kaina – 450 eurų", 450),
    ("€720 month rent", 720),
    ("Apartment in Užupis, 500 eur/mėn + utilities", 500),
    ("Kaina 500€, užstatas 250€", 500),
    ("Nuomoju butą Užupyje, susisiekite", None),
    ("Tel +37060012345 metai 2026", None),
    ("Užstatas 50 eur", None),
    ("Kaina 8000 EUR", None),
])
def test_extract_price(text, expected):
    assert extract_price(text) == expected
